#!/usr/bin/env python3

import yaml
import argparse
import pprint
import copy

def convert_openapi_to_jsonschema(input_path):
    with open(input_path, 'r') as infile:
        openapi_data = yaml.safe_load(infile)

    return build_schema_dict_from_post_paths(openapi_data)


def build_schema_dict_from_post_paths(openapi_data):
    """
    Build a dictionary of resources based on POST paths with 201 responses.
    """
    schema_dict = {}
    for path, methods in openapi_data.get('paths', {}).items():
        # Skip paths containing '{'
        if '{' in path:
            continue

        #if path != '/api/v2/broadcasters' and path != '/api/v2/signups':
        # if path != '/api/v2/signups':
        #    continue

        for method in ['post', 'get']:
            if method in methods:
                if method == 'post':
                    schema = methods[method].get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
                if method == 'get':
                    # For GET, schema might be in the response
                    schema = methods[method].get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
                    if '$ref' not in schema:
                        # If there's no $ref, we can use the schema directly
                        schema = schema.get('properties', {})

                if schema:
                    # Extract the resource name from the path
                    resource_name = path.split('/')[-1]
                    attributes = extract_attributes(schema, openapi_data)
                    if resource_name not in schema_dict:
                        schema_dict[resource_name] = {'properties': attributes}
                    else:
                        # Merge attributes, removing duplicates
                        existing_attributes = schema_dict[resource_name]['properties']
                        schema_dict[resource_name]['properties'] = {**existing_attributes, **attributes}

    return merge_relationships_into_schema(schema_dict, relationships)

def merge_relationships_into_schema(schema_dict, relationships):
    """
    Merge relationship properties into the schema dictionary.
    """
    for resource_name, schema_data in schema_dict.items():
        if resource_name in relationships:
            # Get the relationship properties
            relationship_properties = relationships[resource_name].get("properties", {})
            # Merge the relationship properties into the schema properties
            schema_data["properties"].update(relationship_properties)
    return schema_dict

def extract_attributes(schema, openapi_data):
    """
    Extract attributes from [data][attributes], handle allOf, and recursively dereference $ref.
    """
    if not isinstance(schema, dict):
        return {}

    def dereference(schema):
        if '$ref' in schema:
            # Call extract_ref to resolve the $ref
            ref_path = schema['$ref'].lstrip('#/').split('/')
            ref_data = openapi_data
            for key in ref_path:
                ref_data = ref_data.get(key, {})
            if ref_data.get('type') == 'object':
                ref_data = ref_data.get('properties', {})
            if 'data' in ref_data:
                if ref_data['data'].get('type') == 'array':
                    ref_data = ref_data['data'].get('items', {})
                else:
                    ref_data = ref_data.get('data').get('properties', {}).get('attributes', {})

            if 'attributes' in ref_data:
                ref_data = ref_data['attributes']

            if 'allOf' in ref_data:
                merged_properties = {}
                for item in ref_data['allOf']:
                    merged_properties.update(dereference(item))
                ref_data = merged_properties

            del schema['$ref']
            schema.update(ref_data)
            return dereference(schema)
        return schema

    schema = dereference(schema)

    for key, value in list(schema.items()):
        # Don't know how to handle objects yet
        if value.get('type') == 'object':
            if key.endswith("address_attributes"):
              # Perform specific actions for keys ending with "address_attributes"
              value['properties'] = copy.deepcopy(address_properties)
              schema[key[:-11]] = value
            del schema[key]
        if value.get('nullable', False) and not isinstance(value.get('type'), list) and 'null' not in value.get('type'):
            value['type'] = ['null', value['type']]
    
    return schema

    item.update(extract_attributes(ref_data, openapi_data)) 
    
    # Iterate through the openapi_data to find and process schemas
    for key, value in openapi_data.items():
      if isinstance(value, dict):
        extract_attributes(value, openapi_data)

    # Navigate to [data][attributes]
    print(f'Extracting attributes from schema: {schema}')
    data = schema.get('properties', {}).get('data', {})
    attributes = data.get('properties', {}).get('attributes', {})



    # Handle $ref in attributes
    if '$ref' in attributes:
        ref_path = attributes['$ref'].lstrip('#/').split('/')
        ref_data = openapi_data
        for key in ref_path:
            ref_data = ref_data.get(key, {})
        return extract_attributes(ref_data, openapi_data)

    # Handle allOf in attributes
    if 'allOf' in attributes:
        merged_properties = {}
        for item in attributes['allOf']:
            merged_properties.update(extract_attributes(item, openapi_data))
        return merged_properties

    # Extract and dereference properties
    properties = {}
    for prop_name, prop_details in attributes.get('properties', {}).items():
        if '$ref' in prop_details:
            # Recursively dereference $ref
            ref_path = prop_details['$ref'].lstrip('#/').split('/')
            ref_data = openapi_data
            for key in ref_path:
                ref_data = ref_data.get(key, {})
            properties[prop_name] = extract_attributes(ref_data, openapi_data)
        else:
            # Include the property as-is
            properties[prop_name] = prop_details

    return properties

address_properties = {
  "address1": {"type": ["string", "null"], "nullable": True},
  "address2": {"type": ["string", "null"], "nullable": True},
  "address3": {"type": ["string", "null"], "nullable": True},
  "city": {"type": ["string", "null"], "nullable": True},
  "state": {"type": ["string", "null"], "nullable": True},
  "zip": {"type": ["string", "null"], "nullable": True},
  "county": {"type": ["string", "null"], "nullable": True},
  "country_code": {"type": ["string", "null"], "nullable": True},
  "lat": {"type": ["string", "null"], "nullable": True},
  "lng": {"type": ["string", "null"], "nullable": True},
  "fips": {"type": ["string", "null"], "nullable": True},
  "submitted_address": {"type": ["string", "null"], "nullable": True},
  "distance": {"type": ["number", "null"], "nullable": True},
  "import_id": {"type": ["string", "null"], "nullable": True},
  "work_phone": {"type": ["string", "null"], "nullable": True},
  "phone_number": {"type": ["string", "null"], "nullable": True},
  "phone_country_code": {"type": ["string", "null"], "nullable": True},
  "work_phone_number": {"type": ["string", "null"], "nullable": True},
  "delete": {"type": ["boolean", "null"], "nullable": True, "default": False},
}
    
relationships = {
  "automation_enrollments": {
    "properties": {
      "automation": { "relation": "to-one", "resource": ["automations"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "automations": {
    "properties": {
      "enrollments": { "relation": "to-many", "resource": ["automation_enrollments"] }
    }
  },
  "ballots": {
    "properties": {
      "election": { "relation": "to-one", "resource": ["elections"] },
      "voter": { "relation": "to-one", "resource": ["voters"] }
    }
  },
  "broadcasters": {
    "properties": {
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "voicemail_point_person": { "relation": "to-one", "resource": ["signups"] },
      "text_point_person": { "relation": "to-one", "resource": ["signups"] },
      "mailings": { "relation": "to-many", "resource": ["mailings"] },
      "signups": { "relation": "to-many", "resource": ["signups"] }
    }
  },
  "contacts": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] },
      "author": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "donations": {
    "properties": {
      "author": { "relation": "to-one", "resource": ["signups"] },
      "donation_tracking_code": { "relation": "to-one", "resource": ["donation_tracking_codes"] },
      "import": { "relation": "to-one", "resource": ["imports"] },
      "membership": { "relation": "to-one", "resource": ["memberships"] },
      "page": { "relation": "to-one", "resource": ["pages"] },
      "payment_type": { "relation": "to-one", "resource": ["payment_types"] },
      "pledge": { "relation": "to-one", "resource": ["pledges"] },
      "mailing": { "relation": "to-one", "resource": ["mailings"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "donation_tracking_code": {
    "properties": {
      "donations": { "relation": "to-many", "resource": ["donations"] }
    }
  },
  "elections": {
    "properties": {
      "ballots": { "relation": "to-many", "resource": ["ballots"] }
    }
  },
  "events": {
    "properties": {
      "auto_response_broadcaster": { "relation": "to-one", "resource": ["broadcaster"] },
      "page": { "relation": "to-one", "resource": ["pages"] },
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "tracking_code": { "relation": "to-one", "resource": ["donation_tracking_codes"] },
      "rsvps": { "relation": "to-many", "resource": ["event_rsvps"] },
      "ticket_levels": { "relation": "to-many", "resource": ["event_ticket_levels"] }
    }
  },
  "event_rsvps": {
    "properties": {
      "author": { "relation": "to-one", "resource": ["signups"] },
      "event_page": { "relation": "to-one", "resource": ["events"] },
      "ticket_level": { "relation": "to-one", "resource": ["event_ticket_levels"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "event_ticket_levels": {
    "properties": {
      "event_page": { "relation": "to-one", "resource": ["events"] },
      "rsvps": { "relation": "to-many", "resource": ["event_rsvps"] }
    }
  },
  "imports": {
    "properties": {
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "author": { "relation": "to-one", "resource": ["signups"] },
      "terminator": { "relation": "to-one", "resource": ["signups"] },
      "signups": { "relation": "to-many", "resource": ["signups"] }
    }
  },
  "mailing": {
    "properties": {
      "author": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "memberships": {
    "properties": {
      "donations": { "relation": "to-many", "resource": ["donations"] },
      "membership_type": { "relation": "to-one", "resource": ["membership_types"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "membership_types": {
    "properties": {
      "page": { "relation": "to-one", "resource": ["pages"] },
      "memberships": { "relation": "to-many", "resource": ["memberships"] }
    }
  },
  "pages": {
    "properties": {
      "site": { "relation": "to-one", "resource": ["site"] },
      "membership_types": { "relation": "to-many", "resource": ["membership_types"] }
    }
  },
  "path_histories": {
    "properties": {
      "current_step_point_person": { "relation": "to-one", "resource": ["signups"] },
      "path_journey": { "relation": "to-one", "resource": ["path_journeys"] },
      "path_journey_status_change": { "relation": "to-one", "resource": ["path_journey_status_changes"] },
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "path_journeys": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] },
      "path": { "relation": "to-one", "resource": ["paths"] },
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "current_step_point_person": { "relation": "to-one", "resource": ["signups"] },
      "path_journey_status_change": { "relation": "to-one", "resource": ["path_journey_status_changes"] },
      "current_step": { "relation": "to-one", "resource": ["path_steps"] },
      "path_histories": { "relation": "to-many", "resource": ["path_histories"] }
    }
  },
  "path_journey_status_changes": {
    "properties": {
      "path": { "relation": "to-one", "resource": ["paths"] },
      "path_journeys": { "relation": "to-many", "resource": ["path_journeys"] },
      "path_histories": { "relation": "to-many", "resource": ["path_histories"] }
    }
  },
  "paths": {
    "properties": {
      "path_journeys": { "relation": "to-many", "resource": ["path_journeys"] },
      "path_steps": { "relation": "to-many", "resource": ["path_steps"] },
      "path_journey_status_changes": { "relation": "to-many", "resource": ["path_journey_status_changes"] },
      "default_point_person": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "path_step": {
    "properties": {
      "path": { "relation": "to-one", "resource": ["paths"] },
      "default_point_person": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "petitions": {
    "properties": {
      "petition_signatures": { "relation": "to-many", "resource": ["petition_signatures"] },
      "page": { "relation": "to-one", "resource": ["pages"] }
    }
  },
  "petition_signature": {
    "properties": {
      "page": { "relation": "to-one", "resource": ["pages"] },
      "petition": { "relation": "to-one", "resource": ["petitions"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "pledges": {
    "properties": {
      "author": { "relation": "to-one", "resource": ["signups"] },
      "donation_tracking_code": { "relation": "to-one", "resource": ["donation_tracking_codes"] },
      "page": { "relation": "to-one", "resource": ["pages"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "precincts": {
    "properties": {
      "point_person": { "relation": "to-one", "resource": ["signups"] },
      "signups": { "relation": "to-many", "resource": ["signups"] }
    }
  },
  "relationships": {
    "properties": {
      "first_signup": { "relation": "to-one", "resource": ["signups"] },
      "second_signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "signup_nations": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "signup_profiles": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "signups": {
    "properties": {
      "author": { "relation": "to-one", "resource": ["signups"] },
      "last_contacted_by": { "relation": "to-one", "resource": ["signups"] },
      "page": { "relation": "to-one", "resource": ["pages"] },
      "parent": { "relation": "to-one", "resource": ["signups"] },
      "precinct": { "relation": "to-one", "resource": ["precincts"] },
      "recruiter": { "relation": "to-one", "resource": ["signups"] },
      "signup_profile": { "relation": "to-one", "resource": ["signup_profiles"] },
      "voter": { "relation": "to-one", "resource": ["voters"] },
      "signup_tags": { "relation": "to-many", "resource": ["signup_tags"] },
      "identity_mappings": { "relation": "to-many", "resource": ["identity_mappings"] },
      "memberships": { "relation": "to-many", "resource": ["memberships"] },
      "path_journeys": { "relation": "to-many", "resource": ["path_journeys"] },
      "taggings": { "relation": "to-many", "resource": ["signup_taggings"] },
      "petition_signatures": { "relation": "to-many", "resource": ["petition_signatures"] },
      "signup_nations": { "relation": "to-many", "resource": ["signup_nations"] },
      "signup_sources": { "relation": "to-many", "resource": ["signup_sources"] }
    }
  },
  "signup_source": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "signup_tags": {
    "properties": {
      "signups": { "relation": "to-many", "resource": ["signups"] }
    }
  },
  "signup_tagging": {
    "properties": {
      "tag": { "relation": "to-one", "resource": ["signup_tags"] },
      "signup": { "relation": "to-one", "resource": ["signups"] }
    }
  },
  "site": {
    "properties": {
      "pages": { "relation": "to-many", "resource": ["pages"] }
    }
  },
  "survey_question_possible_responses": {
    "properties": {
      "survey_question": { "relation": "to-one", "resource": ["survey_questions"] },
      "survey_question_responses": { "relation": "to-many", "resource": ["survey_question_responses"] }
    }
  },
  "survey_questions": {
    "properties": {
      "survey": { "relation": "to-one", "resource": ["surveys"] },
      "author": { "relation": "to-one", "resource": ["signups"] },
      "survey_question_responses": { "relation": "to-many", "resource": ["survey_question_responses"] },
      "survey_question_possible_responses": { "relation": "to-many", "resource": ["survey_question_possible_responses"] }
    }
  },
  "survey_question_responses": {
    "properties": {
      "survey_question": { "relation": "to-one", "resource": ["survey_questions"] },
      "survey_question_possible_response": { "relation": "to-one", "resource": ["survey_question_possible_responses"] },
      "signup": { "relation": "to-one", "resource": ["signups"] },
      "author": { "relation": "to-one", "resource": ["signups"] },
      "page": { "relation": "to-one", "resource": ["pages"] }
    }
  },
  "surveys": {
    "properties": {
      "survey_questions": { "relation": "to-many", "resource": ["survey_questions"] }
    }
  },
  "voters": {
    "properties": {
      "signup": { "relation": "to-one", "resource": ["signups"] },
      "ballots": { "relation": "to-many", "resource": ["ballots"] }
    }
  }
}



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert OpenAPI YAML to flattened schema dictionary")
    parser.add_argument("input", help="Path to OpenAPI YAML file")
    parser.add_argument("output", help="Path to output schema dictionary YAML file")
    args = parser.parse_args()

    schema_dict = convert_openapi_to_jsonschema(args.input)
    # Write to output YAML
    with open(args.output, 'w') as outfile:
        yaml.dump(schema_dict, outfile, sort_keys=False)
        print(f"Schema dictionary written to {args.output}")

