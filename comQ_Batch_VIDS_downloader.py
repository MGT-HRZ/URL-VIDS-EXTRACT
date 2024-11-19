import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, parse_qs
import re
from concurrent.futures import ThreadPoolExecutor  # For parallel downloading
from tqdm import tqdm  # Import tqdm for the progress bar

# Step 1: Save the webpage source as index.html
def save_page_source(url, filename="index.html"):
    try:
        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status()

        # Save the page source as index.html
        with open(filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"Page source saved to {filename}.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the website: {e}")

# Step 2: Extract video links from the saved HTML page
def extract_video_links_from_html(filename="index.html", max_videos=10):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
        
        # Find all anchor tags that contain video links
        a_tags = soup.find_all("a", href=re.compile(r"\.(mp4|webm|mkv)$", re.IGNORECASE))
        valid_videos = []
        count = 0

        for a_tag in a_tags:
            if count >= max_videos:
                break
            video_url = a_tag.get("href")
            if not video_url:
                continue

            # Handle relative URLs
            if video_url.startswith("//"):
                video_url = f"http:{video_url}"
            elif video_url.startswith("/"):
                video_url = f"{url.rstrip('/')}{video_url}"

            valid_videos.append(video_url)
            count += 1

        return valid_videos
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

# Step 3: Save the video links to an HTML file (videos.html)
def save_videos_to_html(video_links, output_file="videos.html"):
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            # Write basic HTML structure with styling
            file.write(""" 
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Extracted Videos</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        margin: 0;
                        padding: 20px;
                    }
                    h1 {
                        text-align: center;
                        color: #333;
                    }
                    .gallery {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 15px;
                        justify-content: center;
                    }
                    .gallery video {
                        max-width: 300px;
                        max-height: 200px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }
                </style>
            </head>
            <body>
                <h1>Extracted Videos</h1>
                <div class="gallery">
            """)
            # Add videos
            for video_link in video_links:
                file.write(f'<video controls><source src="{video_link}" type="video/mp4"></video>')
            file.write(""" 
                </div>
            </body>
            </html>
            """)
        print(f"Videos saved to {output_file}.")
    except Exception as e:
        print(f"Error saving videos to HTML: {e}")

# Step 4: Sanitize the filename
def sanitize_filename(video_url):
    """Sanitize the filename by extracting it from the URL query string."""
    
    # Check if the URL has a query string with 'f='
    parsed_url = urlsplit(video_url)
    query_params = parse_qs(parsed_url.query)
    
    # If there's a query parameter 'f', use it to extract the filename
    if 'f' in query_params:
        filename = query_params['f'][0]  # Get the filename from the 'f' parameter
    else:
        # Fallback to the base name from the URL path if 'f' is not present
        filename = os.path.basename(parsed_url.path)

    # Print to check the filename before sanitization
    print(f"Base filename before sanitization: {filename}")

    # Remove '%20' (space encoding) completely
    filename = filename.replace('%20', '')  # Remove '%20' (spaces)

    # Optionally, sanitize any other unwanted characters (e.g., invalid filesystem characters)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    print(f"Sanitized filename after removing invalid characters: {filename}")
    
    return filename

# Step 5: Download video
def download_video(video_url, download_folder="downloaded_videos"):
    """Download video from the URL and save it to the specified folder."""
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    try:
        print(f"Downloading {video_url}...")

        # Add headers to simulate a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        video_response = requests.get(video_url, headers=headers, stream=True)
        video_response.raise_for_status()

        # Check if the response content type is a video
        content_type = video_response.headers.get('Content-Type', '')
        if 'video' not in content_type:
            print(f"Skipping {video_url} (not a video).")
            return False  # Return False if the video isn't downloaded

        # Get the sanitized video filename
        video_name = sanitize_filename(video_url)  # Sanitize filename to keep the desired part
        video_path = os.path.join(download_folder, video_name)

        # Check if filename exists already, then add a number to avoid overwriting
        if os.path.exists(video_path):
            base_name, ext = os.path.splitext(video_name)
            counter = 1
            while os.path.exists(video_path):
                video_name = f"{base_name}_{counter}{ext}"
                video_path = os.path.join(download_folder, video_name)
                counter += 1

        # Download video with progress bar
        with open(video_path, "wb") as video_file:
            total_size = int(video_response.headers.get('Content-Length', 0))
            chunk_size = 1024  # Download in 1k chunks
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=video_name) as pbar:
                for chunk in video_response.iter_content(chunk_size=chunk_size):
                    video_file.write(chunk)
                    pbar.update(len(chunk))

        print(f"Saved {video_name} to {download_folder}.")
        return True  # Return True if download was successful
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {video_url}: {e}")
        return False  # Return False if download failed

# Step 6: Ask user to download or skip the video
def ask_user_to_download_video(video_url):
    """Ask the user whether to download the video or not"""
    response = input(f"Do you want to download this video? {video_url} (1 for yes, 2 for no): ").strip()
    
    if response == "1":
        return video_url  # Return the video URL to be downloaded
    elif response == "2":
        print(f"Skipping video: {video_url}")
        return None
    else:
        print("Invalid input. Please enter '1' for yes or '2' for no.")
        return ask_user_to_download_video(video_url)

# Step 7: Download selected videos concurrently
def download_videos_concurrently(selected_videos, download_folder="downloaded_videos"):
    """Download multiple videos concurrently with a progress bar."""
    downloaded_count = 0  # Counter for successfully downloaded videos

    # Using ThreadPoolExecutor to download videos concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Track successful downloads
        for success in executor.map(lambda video_url: download_video(video_url, download_folder), selected_videos):
            if success:
                downloaded_count += 1

    return downloaded_count

# Main code to execute the steps
if __name__ == "__main__":
    # Hardcoded website URL
    website_url = " "  # Replace with your desired URL

    # Customizable parameters
    max_videos = 0  # Maximum number of videos to extract

    # Step 1: Save the webpage source as index.html
    save_page_source(website_url)

    # Step 2: Extract video links from the saved index.html
    video_links = extract_video_links_from_html("index.html", max_videos)

    # Step 3: Save the extracted videos to videos.html
    save_videos_to_html(video_links)

    # Step 4: Ask the user for each video whether to download it
    selected_videos = []
    for video_url in video_links:
        result = ask_user_to_download_video(video_url)
        if result:
            selected_videos.append(result)

    # Step 5: Download selected videos concurrently with progress bar
    if selected_videos:
        downloaded_count = download_videos_concurrently(selected_videos)

        # Print the total number of videos downloaded
        print(f"\nTotal videos downloaded: ({downloaded_count}/{len(selected_videos)})")

    print("Script finished.")
