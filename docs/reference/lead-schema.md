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

## Flexible Data

- `extra`
- `raw_data`

Serialize a lead with `Lead.to_dict()`.
