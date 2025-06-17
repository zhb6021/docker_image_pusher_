import asyncio
from aiohttp import ClientSession
import json # 用于解析 JSON
from urllib.parse import urlparse # 用于解析 URL
import subprocess
import os
import argparse
import sys
import logging

# Global list of image URLs, can be overridden by command-line argument
image_urls = [
    "https://hub.docker.com/_/nginx/tags",
    "https://hub.docker.com/r/prom/prometheus/tags"
]

def parse_dockerhub_url(image_url):
    path_parts = [part for part in urlparse(image_url).path.split('/') if part]
    if len(path_parts) >= 3 and path_parts[-1] == 'tags':
        if path_parts[0] == '_':
            namespace = "library"
            repository = path_parts[1]
            return namespace, repository
        elif path_parts[0] == 'r' and len(path_parts) >= 4:
            namespace = path_parts[1]
            repository = path_parts[2]
            return namespace, repository
    logging.warning(f"Could not parse Docker Hub URL: {image_url}")
    return None, None


def pull_image(image_name: str, tag: str) -> bool:
    pull_command = f"docker pull {image_name}:{tag}"
    logging.info(f"Pulling image: {image_name}:{tag} with command: '{pull_command}'")
    try:
        result = subprocess.run(pull_command, shell=True, check=True, capture_output=True, text=True)
        logging.info(f"Successfully pulled {image_name}:{tag}")
        # Stderr might contain useful info even on success (e.g. image up to date)
        if result.stdout and result.stdout.strip():
            logging.debug(f"Pull stdout: {result.stdout.strip()}")
        if result.stderr and result.stderr.strip():
             logging.debug(f"Pull stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to pull {image_name}:{tag}. Command: '{e.cmd}' exited with code {e.returncode}")
        if e.stderr:
            logging.error(f"Stderr: {e.stderr.strip()}")
        if e.stdout:
            logging.error(f"Stdout: {e.stdout.strip()}") # Error because it might contain error messages
        return False
    except FileNotFoundError:
        logging.error("Docker command not found. Please ensure Docker is installed and in PATH.")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred while pulling {image_name}:{tag}: {e}")
        return False

def tag_image(original_image_name: str, original_tag: str, target_repo_url: str, new_tag: str) -> bool:
    source_image_ref = f"{original_image_name}:{original_tag}"
    target_image_ref = f"{target_repo_url}/{original_image_name}:{new_tag}"
    tag_command = f"docker tag {source_image_ref} {target_image_ref}"
    logging.info(f"Tagging image {source_image_ref} as {target_image_ref} with command: '{tag_command}'")
    try:
        result = subprocess.run(tag_command, shell=True, check=True, capture_output=True, text=True)
        logging.info(f"Successfully tagged {source_image_ref} as {target_image_ref}")
        if result.stdout and result.stdout.strip(): # Docker tag usually doesn't produce stdout
            logging.debug(f"Tag stdout: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error tagging image. Command: '{e.cmd}' failed with exit code {e.returncode}")
        if e.stderr:
            logging.error(f"Stderr: {e.stderr.strip()}")
        if e.stdout:
            logging.error(f"Stdout: {e.stdout.strip()}")
        return False
    except FileNotFoundError:
        logging.error("Docker command not found. Please ensure Docker is installed and in PATH.")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred while tagging {source_image_ref}: {e}")
        return False

def docker_login(registry_url: str, username: str, password: str) -> bool:
    login_command = f"docker login {registry_url} -u {username} --password-stdin"
    logging.info(f"Attempting to login to {registry_url} as {username}...")
    try:
        result = subprocess.run(login_command, input=password, text=True, shell=True, check=True, capture_output=True)
        # Docker login success message is often on stderr, or stdout depending on version/registry
        # Checking result.stdout and result.stderr for "Login Succeeded" or similar messages is more robust
        # For now, just log the attempt as successful if no error is raised.
        logging.info(f"Docker login command to {registry_url} as {username} executed successfully.")
        if result.stdout and result.stdout.strip():
            logging.info(f"Login stdout: {result.stdout.strip()}")
        if result.stderr and result.stderr.strip(): # Often "Login Succeeded" is here
            logging.info(f"Login stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during Docker login to {registry_url}. Command: '{e.cmd}' failed with exit code {e.returncode}")
        if e.stderr:
            logging.error(f"Stderr: {e.stderr.strip()}")
        if e.stdout:
            logging.error(f"Stdout: {e.stdout.strip()}")
        return False
    except FileNotFoundError:
        logging.error("Docker command not found. Please ensure Docker is installed and in PATH.")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred during Docker login to {registry_url}: {e}")
        return False

def push_image(full_image_reference: str) -> bool:
    push_command = f"docker push {full_image_reference}"
    logging.info(f"Pushing image: {full_image_reference} with command: '{push_command}'")
    try:
        result = subprocess.run(push_command, shell=True, check=True, capture_output=True, text=True)
        logging.info(f"Successfully pushed {full_image_reference}")
        if result.stdout and result.stdout.strip():
            logging.debug(f"Push stdout: {result.stdout.strip()}")
        if result.stderr and result.stderr.strip(): # Push progress might also be on stderr
            logging.debug(f"Push stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error pushing image {full_image_reference}. Command: '{e.cmd}' failed with exit code {e.returncode}")
        if e.stderr:
            logging.error(f"Stderr: {e.stderr.strip()}")
        if e.stdout:
            logging.error(f"Stdout: {e.stdout.strip()}")
        return False
    except FileNotFoundError:
        logging.error("Docker command not found. Please ensure Docker is installed and in PATH.")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred while pushing {full_image_reference}: {e}")
        return False

def is_image_backed_up(image_name: str, tag: str, record_file: str = "backed_up_images.txt") -> bool:
    record_to_check = f"{image_name}:{tag}"
    try:
        if not os.path.exists(record_file):
            logging.debug(f"Record file {record_file} does not exist. Image {record_to_check} is not backed up.")
            return False
        with open(record_file, "r") as f:
            for line in f:
                if line.strip() == record_to_check:
                    logging.info(f"Image {record_to_check} already recorded as backed up in {record_file}.")
                    return True
        logging.debug(f"Image {record_to_check} not found in {record_file}.")
        return False
    except IOError as e:
        logging.error(f"Error reading record file {record_file}: {e}. Assuming not backed up.")
        return False

def record_backup(image_name: str, tag: str, record_file: str = "backed_up_images.txt") -> None:
    record_to_add = f"{image_name}:{tag}"
    try:
        with open(record_file, "a") as f:
            f.write(record_to_add + "\n")
        logging.info(f"Successfully recorded {record_to_add} as backed up in {record_file}.")
    except IOError as e:
        logging.error(f"Error writing to record file {record_file}: {e}")

async def get_tags_data(session, image_url, n=5):
    namespace, repository = parse_dockerhub_url(image_url)
    if not namespace or not repository:
        # Error already logged by parse_dockerhub_url if it fails
        return []

    api_url = f"https://hub.docker.com/v2/repositories/{namespace}/{repository}/tags/?page_size={n}"
    logging.debug(f"Fetching tags from: {api_url}")

    try:
        async with session.get(api_url) as response:
            response.raise_for_status()
            data = await response.json()
            tags = []
            if "results" in data and isinstance(data["results"], list):
                for item in data["results"]:
                    if "name" in item:
                        tags.append({"repository": repository, "tag": item["name"]})
            return tags
    except Exception as e:
        logging.error(f"Error fetching or parsing tags for {image_url}: {e}", exc_info=True)
        return []

async def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description="Backup Docker images from Docker Hub to a target registry.")
    parser.add_argument("-n", "--num-tags", type=int, default=5, help="Number of latest tags to fetch per image. Default: 5")
    parser.add_argument("-r", "--record-file", type=str, default="backed_up_images.txt", help="Path to the backup record file. Default: backed_up_images.txt")
    parser.add_argument("-u", "--image-urls", type=str, help="Comma-separated string of Docker Hub URLs to process. Overrides the hardcoded list.")

    args = parser.parse_args()

    logging.info("--- Configuration Loading ---")
    target_registry_url = os.getenv("TARGET_REGISTRY_URL")
    target_namespace = os.getenv("TARGET_NAMESPACE")
    docker_username = os.getenv("DOCKER_USERNAME")
    docker_password = os.getenv("DOCKER_PASSWORD")

    if not all([target_registry_url, target_namespace, docker_username, docker_password]):
        logging.error("Error: Missing one or more required environment variables: TARGET_REGISTRY_URL, TARGET_NAMESPACE, DOCKER_USERNAME, DOCKER_PASSWORD")
        sys.exit(1)

    logging.info(f"Target Registry URL: {target_registry_url}")
    logging.info(f"Target Namespace: {target_namespace}")
    logging.info(f"Record File: {args.record_file}")
    logging.info(f"Number of tags to fetch per image: {args.num_tags}")

    current_image_urls_to_process = image_urls
    if args.image_urls:
        current_image_urls_to_process = [url.strip() for url in args.image_urls.split(',')]
        logging.info(f"Using provided image URLs: {current_image_urls_to_process}")
    else:
        logging.info(f"Using hardcoded image URLs: {current_image_urls_to_process}")

    logging.info("--- Docker Login ---")
    if not docker_login(target_registry_url, docker_username, docker_password):
        logging.error("Docker login failed. Exiting.")
        sys.exit(1)
    # Success message logged by docker_login or here if preferred
    logging.info("Docker login process completed.")


    logging.info("--- Starting Image Backup Process ---")
    async with ClientSession() as session:
        for source_image_url in current_image_urls_to_process:
            logging.info(f"Processing URL: {source_image_url}")
            source_hub_namespace, source_hub_repo_name = parse_dockerhub_url(source_image_url)

            if not source_hub_repo_name:
                logging.warning(f"Failed to parse Docker Hub URL: {source_image_url}. Skipping.")
                continue

            if source_hub_namespace == "library":
                image_name_on_hub = source_hub_repo_name
            else:
                image_name_on_hub = f"{source_hub_namespace}/{source_hub_repo_name}"

            logging.info(f"Fetching tags for {image_name_on_hub} (up to {args.num_tags} tags)...")
            tags_data = await get_tags_data(session, source_image_url, n=args.num_tags)

            if not tags_data:
                logging.warning(f"No tags found or error fetching tags for {image_name_on_hub}. Skipping.")
                continue

            logging.info(f"Found {len(tags_data)} tags for {image_name_on_hub}. Processing...")

            for image_info in tags_data:
                current_tag = image_info["tag"]
                logging.info(f"Processing tag: {image_name_on_hub}:{current_tag}")

                if is_image_backed_up(image_name_on_hub, current_tag, args.record_file):
                    # Message already logged by is_image_backed_up
                    continue

                logging.info(f"Attempting to pull {image_name_on_hub}:{current_tag}...")
                if not pull_image(image_name_on_hub, current_tag):
                    logging.error(f"Pull failed for {image_name_on_hub}:{current_tag}. Skipping this tag.")
                    continue

                target_repo_base_for_tagging = f"{target_registry_url}/{target_namespace}"
                logging.info(f"Attempting to tag {image_name_on_hub}:{current_tag} for {target_repo_base_for_tagging}...")
                if not tag_image(original_image_name=image_name_on_hub,
                                 original_tag=current_tag,
                                 target_repo_url=target_repo_base_for_tagging,
                                 new_tag=current_tag):
                    logging.error(f"Tagging failed for {image_name_on_hub}:{current_tag}. Skipping this tag.")
                    continue

                full_image_ref_for_push = f"{target_repo_base_for_tagging}/{image_name_on_hub}:{current_tag}"
                logging.info(f"Attempting to push {full_image_ref_for_push}...")
                if not push_image(full_image_ref_for_push):
                    logging.error(f"Push failed for {full_image_ref_for_push}. Skipping this tag.")
                    continue

                logging.info(f"Successfully pulled, tagged, and pushed {image_name_on_hub}:{current_tag} to {full_image_ref_for_push}")
                record_backup(image_name_on_hub, current_tag, args.record_file)

    logging.info("--- Image Backup Process Completed ---")

if __name__ == "__main__":
    asyncio.run(main())
