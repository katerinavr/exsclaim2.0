import json

def find_images_without_labels(json_str):
    """
    Analyze JSON data to find images without any subfigure labels.
    
    Parameters:
    json_str (str): The JSON string containing image data
    
    Returns:
    list: List of dictionaries containing information about images without labels
    """
    try:
        # Parse JSON data
        data = json.loads(json_str)
        
        # Initialize list to store images without labels
        unlabeled_images = []
        
        # Analyze each image entry
        for image in data:
            # Check if Subfigure Label exists and is empty or missing
            if ('Label' not in image or 
                'Subfigure Label' not in image['Label'] or 
                not image['Label']['Subfigure Label']):
                
                # Store relevant information about the unlabeled image
                unlabeled_info = {
                    'External ID': image.get('External ID', 'Unknown'),
                    'Created At': image.get('Created At', 'Unknown'),
                    'Updated At': image.get('Updated At', 'Unknown')
                }
                unlabeled_images.append(unlabeled_info)
        
        return unlabeled_images
    
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def print_results(unlabeled_images):
    """
    Print the results in a formatted way.
    
    Parameters:
    unlabeled_images (list): List of dictionaries containing unlabeled image information
    """
    if not unlabeled_images:
        print("All images have subfigure labels.")
        return
        
    print(f"\nFound {len(unlabeled_images)} images without subfigure labels:\n")
    for img in unlabeled_images:
        print(f"File: {img['External ID']}")
        print(f"Created: {img['Created At']}")
        print(f"Updated: {img['Updated At']}")
        print("-" * 50)

# Example usage:
if __name__ == "__main__":
    # Read the JSON data from a file
    try:
        with open('C:/Users/kvriz/Desktop/exsclaim2.0/yolov11_training_data/export-2024-07-11T05_19_22.318Z.json', 'r') as file:
            json_str = file.read()
            
        # Find images without labels
        unlabeled_images = find_images_without_labels(json_str)
        
        # Print results
        print_results(unlabeled_images)
        
    except FileNotFoundError:
        print("Error: Could not find the input file.")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")