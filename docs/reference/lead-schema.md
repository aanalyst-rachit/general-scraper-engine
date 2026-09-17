# Lead Schema

The main `Lead` model contains these field groups.

## Identity

- `name`
- `profession`
- `company_name`
- `category`
- `subcategory`

## Professional / Business

- `designation`
- `specialization`
- `services`
- `description`

## Contact

- `phone`
- `alternate_phone`
- `email`
- `alternate_email`
- `website`

## Address

- `address`
- `location`
- `locality`
- `city`
- `district`
- `state`
- `country`
- `pincode`

## Public Profiles

- `social_profiles`

## Source / Discovery

- `source_url`
- `source_name`
- `source_id`
- `search_context`

Direct-source adapters such as Google Maps and Justdial populate the same source and identity fields in the common `Lead` model.

## Flexible Data

- `extra`
- `raw_data`

The `category` field represents the normalized business category and can be used by the CLI for exact category filtering.

Serialize a lead with `Lead.to_dict()`.
