#!/usr/bin/env python3
import sys
import yaml

def resolve_ref(ref, schemas):
    """
    Resolve a JSON reference in the format "#/components/schemas/XYZ".
    """
    parts = ref.strip("#/").split("/")
    if len(parts) == 3 and parts[0] == "components" and parts[1] == "schemas":
        ref_name = parts[2]
        return schemas.get(ref_name, {})
    return {}

def merge_allOf(all_of_list, schemas):
    """
    Merge the "properties" from each item in an allOf list.
    Each item may be a $ref or have its own "properties" key.
    """
    merged = {}
    for item in all_of_list:
        if "$ref" in item:
            ref_schema = resolve_ref(item["$ref"], schemas)
            props = ref_schema.get("properties", {})
            merged.update(props)
        else:
            props = item.get("properties", {})
            merged.update(props)
    return merged

def infer_resource_name(name):
    """
    Given the base property name (usually before _id[s]),
    try to determine the name of the related resource.
    """
    mapping = {
        "author": "people",
        "signup": "signups",
        "automation": "automations",
        "ballot": "ballots",
        "broadcaster": "broadcasters",
        "contact": "contacts",
        "custom_field": "custom_fields",
        "donation": "donations",
        "election": "elections",
        "event": "events",
        "membership": "memberships",
        "membership_type": "membership_types",
        "page": "pages",
        "path": "paths",
        "path_journey": "path_journeys",
        "path_step": "path_steps",
        "petition": "petitions",
        "pledge": "pledges",
        "precinct": "precincts",
        "relationship": "relationships",
        "voter": "voters",
        "signup_tag": "signup_tags",
        "signup_tagging": "signup_taggings",
        "site": "sites",
        "survey": "surveys",
        "survey_question": "survey_questions",
        "survey_question_possible_response": "survey_question_possible_responses",
        "survey_question_response": "survey_question_responses"
    }
    key = name.lower()
    return mapping.get(key, key + "s")

def extract_properties(schema, schemas, required_fields):
    """
    Given a schema (which may use allOf) and a list of required fields,
    return a dictionary of property definitions. For each property:
      - If the property name ends in '_id' or '_ids', mark it as a relationship.
      - Otherwise, check if the property is required; if not, output its type as [None, <mapped_type>].
    """
    properties = {}
    if "allOf" in schema:
        merged = merge_allOf(schema["allOf"], schemas)
    elif "properties" in schema:
        merged = schema["properties"]
    else:
        merged = {}

    # Mapping from OpenAPI types to our simplified types.
    type_map = {
        "string": "string",
        "integer": "int",
        "number": "float",
        "boolean": "bool"
    }

    for prop, definition in merged.items():
        # Handle relationships
        if prop.endswith('_ids'):
            base = prop[:-4]
            resource_name = infer_resource_name(base)
            properties[prop] = {"relation": "to-many", "resource": [resource_name]}
        elif prop.endswith('_id'):
            base = prop[:-3]
            resource_name = infer_resource_name(base)
            properties[prop] = {"relation": "to-one", "resource": [resource_name]}
        else:
            orig_type = definition.get("type")
            # If type is a list (e.g. ["null", "string"]), filter out "null" to determine the base type.
            if isinstance(orig_type, list):
                filtered = [t for t in orig_type if t != "null"]
                base_type = filtered[0] if filtered else "string"
            elif isinstance(orig_type, str):
                base_type = orig_type
            else:
                base_type = "string"
            # Map the base type
            base_type = type_map.get(base_type, base_type)
            # If the property is not required, output its type as [None, <mapped_type>]
            if prop in required_fields:
                properties[prop] = {"type": base_type}
            else:
                properties[prop] = {"type": [None, base_type]}
    return properties

def main():
    if len(sys.argv) != 2:
        print("Usage: {} <openapi-spec.yaml>".format(sys.argv[0]))
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        spec = yaml.safe_load(f)

    components = spec.get("components", {})
    schemas = components.get("schemas", {})

    output = {}
    # We iterate over schemas whose name ends with '_response_data'.
    # These typically represent resource responses with a "data" object including "attributes".
    for key, schema in schemas.items():
        if key.endswith("_response_data"):
            # Determine the resource name from the "type" property example if available,
            # otherwise use the key without the suffix.
            type_def = schema.get("properties", {}).get("type", {})
            resource_name = type_def.get("example") if type_def.get("example") else key.replace("_response_data", "")
            # Get the attributes schema and its "required" list, if provided.
            attributes_schema = schema.get("properties", {}).get("attributes", {})
            required_fields = attributes_schema.get("required", []) if attributes_schema else []
            if attributes_schema:
                props = extract_properties(attributes_schema, schemas, required_fields)
                output[resource_name] = {"properties": props}

    # Dump the output as YAML so that it can be loaded into a Python dict.
    print(yaml.dump(output, sort_keys=False))

if __name__ == "__main__":
    main()

