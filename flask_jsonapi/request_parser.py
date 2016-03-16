from collections import namedtuple

from . import _compat, errors

ParseResult = namedtuple('ParseResult', ('id', 'fields'))


class RequestParser(object):
    def __init__(self, resource, id=None):
        self.resource = resource
        self.id = id

    def parse(self, data):
        _ensure_object(data=data, path=[])
        _require_property(data=data, property_='data', path=[])
        return self.parse_resource_object(data=data['data'], path=['data'])

    def parse_resource_object(self, data, path):
        _ensure_object(data=data, path=path)
        _require_property(data=data, property_='type', path=path)
        self._validate_type(
            expected_type=self.resource.type,
            data=data['type'],
            path=path + ['type']
        )
        if self.id is not None:
            _require_property(data=data, property_='id', path=path)
        if 'id' in data:
            _ensure_string(data=data['id'], path=path + ['id'])
            if self.id is not None and data['id'] != self.id:
                raise errors.IDMismatch(data['id'])
            if (
                self.id is None and
                not self.resource.allow_client_generated_ids
            ):
                raise errors.ClientGeneratedIDsUnsupported(self.resource.type)
        return ParseResult(
            id=data.get('id'),
            fields=self.parse_fields(data, path)
        )

    def parse_fields(self, data, path):
        fields = {}
        fields.update(
            self.parse_attributes_object(
                data=data.get('attributes', {}),
                path=path + ['attributes']
            )
        )
        fields.update(
            self.parse_relationships_object(
                data=data.get('relationships', {}),
                path=path + ['relationships']
            )
        )
        return fields

    def parse_attributes_object(self, data, path):
        _ensure_object(data, path)
        self._check_extra_attributes(data, path)
        return data

    def _check_extra_attributes(self, data, path):
        for attribute_name in data:
            self._check_extra_attribute(
                attribute_name=attribute_name,
                path=path + [attribute_name]
            )

    def _check_extra_attribute(self, attribute_name, path):
        if attribute_name not in self.resource.attributes:
            raise errors.ValidationError(
                detail=(
                    '{attribute!r} is not a valid attribute for {type!r} '
                    'resource'
                ).format(attribute=attribute_name, type=self.resource.type),
                source_pointer=json_pointer_from_path(path)
            )

    def _parse_resource_linkage(
        self,
        relationship,
        data,
        path,
        ignore_not_found=False
    ):
        if relationship.many:
            return self._parse_to_many_resource_linkage(
                relationship=relationship,
                data=data,
                path=path,
                ignore_not_found=ignore_not_found
            )
        else:
            return self._parse_to_one_resource_linkage(
                relationship=relationship,
                data=data,
                path=path
            )

    def _parse_to_many_resource_linkage(
        self,
        relationship,
        data,
        path,
        ignore_not_found=False
    ):
        objs = []
        _ensure_array(data, path)
        for index, resource_identifier in enumerate(data):
            try:
                obj = self._parse_resource_identifier(
                    resource=relationship.resource,
                    data=resource_identifier,
                    path=path + [str(index)]
                )
                objs.append(obj)
            except errors.ResourceNotFound:
                if not ignore_not_found:
                    raise
        return objs

    def _validate_type(self, expected_type, data, path):
        _ensure_string(data=data, path=path)
        if data != expected_type:
            raise errors.TypeMismatch(
                type=data,
                source_pointer=json_pointer_from_path(path)
            )


def _ensure_string(data, path):
    if not isinstance(data, _compat.string_types):
        raise errors.ValidationError(
            detail="{!r} is not of type 'string'".format(data),
            source_pointer=json_pointer_from_path(path)
        )


def _ensure_object(data, path):
    if not isinstance(data, dict):
        raise errors.ValidationError(
            detail="{!r} is not of type 'object'".format(data),
            source_pointer=json_pointer_from_path(path)
        )


def _ensure_array(data, path):
    if not isinstance(data, list):
        raise errors.ValidationError(
            detail="{!r} is not of type 'array'".format(data),
            source_pointer=json_pointer_from_path(path)
        )


def _require_property(data, property_, path):
    if property_ not in data:
        raise errors.ValidationError(
            detail="{!r} is a required property".format(property_),
            source_pointer=json_pointer_from_path(path)
        )


def json_pointer_from_path(path):
    return '/' + '/'.join(path)
