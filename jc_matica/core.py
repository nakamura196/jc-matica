# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['ApiClient']

# %% ../nbs/00_core.ipynb 3
import requests
import os
from bs4 import BeautifulSoup
import pandas as pd
import boto3
from dotenv import load_dotenv
from botocore.config import Config
from tqdm import tqdm

# %% ../nbs/00_core.ipynb 4
class ApiClient:
    """
    API Client for Archivematica

    Args:
        env_path: Path to the environment variables file
    """
    def __init__(self, env_path: str = ".env"):
        load_dotenv(override=True, dotenv_path=env_path)

    def upload(self, prefix, id, output_dir):
        """
        Upload an AIP to Archivematica

        Args:
            prefix: The prefix of the repository
            id: The ID of the record

            output_dir: The directory to save the AIP
        """
        url = f"https://{prefix}.repo.nii.ac.jp/records/{id}/export/json"

        response = requests.get(url)

        data = response.json()

        attribute_value_mlt_list = data["metadata"]["item_files"]["attribute_value_mlt"]

        filenames = []

        output_item_dir = f"{output_dir}/{prefix}_{id}"

        for file in attribute_value_mlt_list:
            url = file["url"]["url"]
            label = file["version_id"] + "." + file["filename"].split(".")[-1]

            opath = f"{output_item_dir}/{label}"

            os.makedirs(os.path.dirname(opath), exist_ok=True)

            with open(opath, "wb") as f:

                # download file
                response = requests.get(url)
                f.write(response.content)

                filenames.append(label)

        oai_url = f"https://{prefix}.repo.nii.ac.jp/oai?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:{prefix}.repo.nii.ac.jp:{id.zfill(8)}"


        response = requests.get(oai_url)

        soup = BeautifulSoup(response.text, "xml")


        record = soup.find("record")


        oai_dc = record.find("oai_dc:dc")

        children = oai_dc.findChildren()

        mappings = {}

        for child in children:

            name = child.name
            text = child.text

            if name not in mappings:
                mappings[name] = []

            mappings[name].append(text)

        rows = []

        for filename in filenames:
            row = {
                "filename": f"objects/{filename}"
            }

            for name, texts in mappings.items():
                row[f"dc.{name}"] = "|".join(texts)

            rows.append(row)

        df = pd.DataFrame(rows)

        opath = f"{output_item_dir}/metadata/metadata.csv"

        os.makedirs(os.path.dirname(opath), exist_ok=True)

        df.to_csv(opath, index=False)

        

        s3 = boto3.client(
            "s3",
            endpoint_url="https://s3ds.mdx.jp",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=Config(
                # signature_version='s3v4',
                s3={
                    'response_checksum_validation': 'when_required',
                    'request_checksum_calculation': 'when_required'
                }
            )
        )

        key_dir = os.getenv("OS_TRANSFER_PREFIX")
        bucket_name = os.getenv("OS_BUCKET_NAME")

        objects = [
            opath
        ]

        

        for filename in filenames:
            opath = f"{output_item_dir}/{filename}"
            objects.append(opath)

        for opath in tqdm(objects):

            s3.upload_file(
                opath,
                bucket_name,
                opath.replace(output_dir, key_dir)
            )
