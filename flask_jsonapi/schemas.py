def get_create_request_schema(resource):
    return {
        "definitions": {
            "resource": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "attributes": {"$ref": "#/definitions/attributes"},
                    "relationships": {"$ref": "#/definitions/relationships"}
                }
            },
            "attributes": _get_attributes_definition(resource),
            "relationships": _get_relationships_definition(resource),
            "relationshipToOne": {
                "type": ["null", "object"],
                "required": [
                    "type",
                    "id"
                ],
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"}
                }
            },
            "relationshipToMany": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "type",
                        "id"
                    ],
                    "properties": {
                        "type": {"type": "string"},
                        "id": {"type": "string"}
                    }
                }
            }
        },
        "type": "object",
        "required": ["data"],
        "properties": {
            "data": {"$ref": "#/definitions/resource"}
        }
    }


def _get_attributes_definition(resource):
    return {
        "type": "object",
        "properties": {
            attribute: {}
            for attribute in resource.attributes
        },
        "additionalProperties": False
    }


def _get_relationships_definition(resource):
    return {
        "type": "object",
        "properties": {
            relationship.name: _get_relationship_definition(
                resource,
                relationship
            )
            for relationship in resource.relationships.values()
        },
        "additionalProperties": False
    }


def _get_relationship_definition(resource, relationship):
    if relationship.many:
        ref = "#/definitions/relationshipToMany"
    else:
        ref = "#/definitions/relationshipToOne"
    return {
        "type": "object",
        "required": ["data"],
        "properties": {
            "data": {"$ref": ref}
        }
    }