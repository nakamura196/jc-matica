import gradio as gr
from jc_matica.core import ApiClient
from archivematica_tools.api import ArchivematicaAPIClient
from archivematica_tools.vis import VisClient
from dotenv import load_dotenv
import os

def process_data(url: str):
    # Load environment variables
    load_dotenv(dotenv_path=".env", override=True)
    client = ApiClient(env_path=".env")
    
    # Parse URL to extract repository prefix and ID
    prefix = url.split("/")[2].split(".")[0]
    id = url.split("/")[-1]
    name = f"{prefix}_{id}"    

    try:
        
        output_dir = "./data"
        # Get environment variables
        location_uuid = os.getenv("LOCATION_UUID")
        processing_config = os.getenv("PROCESSING_CONFIG")
        path = f"jc/{name}"
        
        # Upload data
        client.upload(prefix, id, output_dir)
        
        # Process with Archivematica
        sip_uuid = ArchivematicaAPIClient.main(
            transfer_type="standard",
            transfer_accession="",
            location_uuid=location_uuid,
            path=path,
            name=name,
            processing_config=processing_config,
            env_path=".env"
        )
        
        # Set up S3 client
        vis = VisClient(
            endpoint_url=os.getenv("OS_ENDPOINT"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            bucket_name=os.getenv("OS_BUCKET_NAME"),
            aip_prefix=os.getenv("OS_AIP_PREFIX")
        )
        
        # Download the processed ZIP file
        local_file, _ = vis.download_zip(sip_uuid, os.getenv("OS_BUCKET_NAME"))
        
        return [f"処理が完了しました。SIP UUID: {sip_uuid}", local_file]
        
    except Exception as e:
        print(f"エラーが発生: {str(e)}")
        return [f"エラーが発生しました: {str(e)}", None]

# Gradio interface
demo = gr.Interface(
    fn=process_data,
    inputs=[
        gr.Textbox(
            label="URL", 
            placeholder="https://kanazawa-u.repo.nii.ac.jp/records/26572",
            value="https://kanazawa-u.repo.nii.ac.jp/records/26572"
        )
    ],
    outputs=[
        gr.Textbox(label="処理結果"),
        gr.File(label="ダウンロード")
    ],
    title="WEKO x Archivematica",
    description="WEKOで公開されているデータからAIPを作成するツール",
    allow_flagging="never"
)

# Launch interface
if __name__ == "__main__":
    demo.launch()