from __future__ import absolute_import

import sqlalchemy
from sqlalchemy import orm

from .. import exceptions


class SQLAlchemyStore(object):
    def __init__(self, session):
        self.session = session

    def fetch(self, model_class, params=None):
        query = self.query(model_class)
        if params:
            query = self._include_related(query, params.include)
            query = self._paginate(query, params.pagination)
        return query.all()

    def fetch_one(self, model_class, id, params=None):
        query = self.query(model_class).filter_by(id=id)
        if params:
            query = self._include_related(query, params.include)
        try:
            return query.one()
        except orm.exc.NoResultFound:
            raise exceptions.ObjectNotFound

    def get_related(self, instance, relationship):
        return getattr(instance, relationship)

    def count_related(self, instance, relationship):
        return self._query_related(instance, relationship).count()

    def fetch_related(self, instance, relationship, params=None):
        if self.is_to_many_relationship(instance.__class__, relationship):
            return self._fetch_many_related(instance, relationship, params)
        else:
            return self._fetch_one_related(instance, relationship, params)

    def _fetch_one_related(self, instance, relationship, params):
        query = self._query_related(instance, relationship)
        if params:
            query = self._include_related(query, params.include)
        try:
            return query.one()
        except orm.exc.NoResultFound:
            return None

    def _fetch_many_related(self, instance, relationship, params):
        query = self._query_related(instance, relationship)
        if params:
            query = self._include_related(query, params.include)
            query = self._paginate(query, params.pagination)
        return query.all()

    def _query_related(self, instance, relationship):
        related_model_class = self.get_related_model_class(
            instance.__class__,
            relationship
        )
        relationship_property = self._get_relationship_property(
            instance.__class__,
            relationship
        )
        query = self.session.query(related_model_class)
        query = query.filter(relationship_property._with_parent(instance))
        if relationship_property.order_by:
            query = query.order_by(*relationship_property.order_by)
        return query

    def count(self, model_class):
        return self.query(model_class).count()

    def query(self, model_class):
        return self.session.query(model_class)

    def _include_related(self, query, include):
        paths = [] if include is None else include.paths
        for path in paths:
            option = orm.subqueryload(path[0])
            for relation in path[1:]:
                option = option.subqueryload(relation)
            query = query.options(option)
        return query

    def _paginate(self, query, pagination):
        if pagination is not None:
            query = query.offset(pagination.offset).limit(pagination.limit)
        return query

    def create(self, model_class, id, fields):
        if id is not None and self._exists(model_class, id):
            raise exceptions.ObjectAlreadyExists
        instance = model_class(id=id, **fields)
        self.session.add(instance)
        self.session.commit()
        return instance

    def update(self, instance, fields):
        for name, value in fields.items():
            setattr(instance, name, value)
        self.session.commit()

    def _exists(self, model_class, id):
        query = self.session.query(model_class).filter_by(id=id)
        return self.session.query(query.exists()).scalar()

    def delete(self, instance):
        self.session.delete(instance)
        self.session.commit()

    def create_relationship(self, instance, relationship, values):
        collection = getattr(instance, relationship)
        for value in values:
            collection.append(value)
        self.session.commit()

    def delete_relationship(self, instance, relationship, values):
        collection = getattr(instance, relationship)
        for value in values:
            try:
                collection.remove(value)
            except ValueError:
                pass
        self.session.commit()

    def get_related_model_class(self, model_class, relationship):
        prop = self._get_relationship_property(model_class, relationship)
        return prop.mapper.class_

    def get_attribute(self, instance, attribute):
        return getattr(instance, attribute)

    def get_id(self, instance):
        return str(instance.id)

    def is_to_many_relationship(self, model_class, relationship):
        mapper = sqlalchemy.inspect(model_class)
        return mapper.relationships[relationship].uselist

    def validate_relationship(self, model_class, relationship):
        self._get_relationship_property(model_class, relationship)

    def _get_relationship_property(self, model_class, relationship):
        mapper = sqlalchemy.inspect(model_class)
        try:
            return mapper.relationships[relationship]
        except KeyError:
            raise exceptions.InvalidRelationship(model_class, relationship)
