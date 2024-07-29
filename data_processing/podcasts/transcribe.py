import boto3
import time
import requests
# Initialize the AWS Transcribe client
transcribe = boto3.client('transcribe', region_name='YOUR_AWS_REGION')

# Function to start a transcription job
def start_transcription_job(audio_file_uri, job_name, language_code='en-US'):
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': audio_file_uri},
        MediaFormat='mp3',  # Adjust if using a different format
        LanguageCode=language_code
    )

# Function to get the transcript text from the completed job
def get_transcript_text(job_name):
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Not ready yet...")
        time.sleep(5)
    
    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        response = requests.get(transcript_url)
        return response.json()['results']['transcripts'][0]['transcript']
    else:
        raise Exception("Transcription failed")

# Main function to transcribe audio and save to a file
def transcribe_audio_to_text(audio_file_uri, job_name, output_file_path):
    start_transcription_job(audio_file_uri, job_name)
    transcript_text = get_transcript_text(job_name)
    
    with open(output_file_path, 'w') as f:
        f.write(transcript_text)

# Example usage
audio_file_uri = 's3://YOUR_BUCKET_NAME/podcast-data/84A28157-6FCD-4277-A2C2-9EF1B95C64DD.mp3'
job_name = 'PodcastTranscribe2'
output_file_path = 'transcript.txt'

transcribe_audio_to_text(audio_file_uri, job_name, output_file_path)
