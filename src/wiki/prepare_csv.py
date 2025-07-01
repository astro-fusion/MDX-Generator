import pandas as pd

def prepare_celebrities_csv(self) -> pd.DataFrame:
  """Prepare celebrities data for CSV import to Supabase."""
  csv_data = []
  
  for celebrity in self.celebrities_data:
      csv_row = {
          'public_id': celebrity.get('public_id'),
          'wikipedia_id': celebrity.get('wikipedia_id'),
          'wikipedia_slug': celebrity.get('wikipedia_slug'),
          'wikipedia_url': celebrity.get('wikipedia_url'),
          'name': celebrity.get('name'),
          'full_name': celebrity.get('full_name'),
          'birth_name': celebrity.get('birth_name'),
          'other_names': json.dumps(celebrity.get('other_names', [])),
          'date_of_birth': celebrity.get('date_of_birth'),
          'birth_date_parsed': celebrity.get('birth_date_parsed'),
          'place_of_birth': celebrity.get('place_of_birth'),
          'birth_time': celebrity.get('birth_time'),
          'birth_coordinates_lat': celebrity.get('birth_coordinates_lat'),
          'birth_coordinates_lng': celebrity.get('birth_coordinates_lng'),
          'birth_timezone': celebrity.get('birth_timezone'),
          'date_of_death': celebrity.get('date_of_death'),
          'death_date_parsed': celebrity.get('death_date_parsed'),
          'place_of_death': celebrity.get('place_of_death'),
          'death_coordinates_lat': celebrity.get('death_coordinates_lat'),
          'death_coordinates_lng': celebrity.get('death_coordinates_lng'),
          'occupation': celebrity.get('occupation'),
          'nationality': celebrity.get('nationality'),
          'citizenship': json.dumps(celebrity.get('citizenship', [])),
          'religion': celebrity.get('religion'),
          'zodiac_sign': celebrity.get('zodiac_sign'),
          'height': celebrity.get('height'),
          'weight': celebrity.get('weight'),
          'eye_color': celebrity.get('eye_color'),
          'hair_color': celebrity.get('hair_color'),
          'profile_summary': celebrity.get('profile_summary'),
          'short_bio': celebrity.get('short_bio'),
          'profile_image_url': celebrity.get('profile_image_url'),
          'profile_image_caption': celebrity.get('profile_image_caption'),
          'spouse': json.dumps(celebrity.get('spouse', [])),
          'children': json.dumps(celebrity.get('children', [])),
          'parents': json.dumps(celebrity.get('parents', {})),
          'siblings': json.dumps(celebrity.get('siblings', [])),
          'years_active': celebrity.get('years_active'),
          'debut_work': celebrity.get('debut_work'),
          'debut_year': celebrity.get('debut_year'),
          'awards': json.dumps(celebrity.get('awards', [])),
          'notable_works': json.dumps(celebrity.get('notable_works', [])),
          'external_urls': json.dumps(celebrity.get('external_urls', {})),
          'social_media': json.dumps(celebrity.get('social_media', {})),
          'is_verified': celebrity.get('is_verified', False),
          'verification_source': celebrity.get('verification_source'),
          'time_verified': celebrity.get('time_verified'),
          'data_quality_score': celebrity.get('data_quality_score', 0),
          'last_updated': celebrity.get('last_updated'),
          'created_at': celebrity.get('created_at')
      }
      
      csv_data.append(csv_row)
  
  return pd.DataFrame(csv_data)
    

def prepare_categories_csv(self) -> pd.DataFrame:
    """Prepare categories for CSV import."""
    categories_set = set()
    
    for celebrity_cat in self.celebrity_categories_data:
        category_name = celebrity_cat['category_name']
        category_group = self.get_category_group(category_name)
        
        categories_set.add((
            category_name,
            self.create_category_slug(category_name),
            f"Category for {category_name} professionals",
            category_group,
            True,
            datetime.now().isoformat()
        ))
    
    df = pd.DataFrame(list(categories_set), columns=[
        'category_name', 'category_slug', 'category_description',
        'category_group', 'is_active', 'created_at'
    ])
    
    return df

def prepare_celebrity_categories_csv(self) -> pd.DataFrame:
    """Prepare celebrity-category relationships for CSV import."""
    csv_data = []
    for rel in self.celebrity_categories_data:
        csv_data.append({
            'celebrity_public_id': rel['celebrity_public_id'],
            'category_name': rel['category_name'],
            'is_primary': rel['is_primary'],
            'confidence_score': rel['confidence_score'],
            'source': rel['source'],
            'added_at': rel['added_at']
        })
    
    return pd.DataFrame(csv_data)