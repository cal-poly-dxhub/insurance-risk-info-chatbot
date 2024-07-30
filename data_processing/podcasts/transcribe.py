import boto3
import time
import requests
import json
import vlc

# Initialize the AWS Transcribe client
transcribe = boto3.client('transcribe', region_name='YOUR_AWS_REGION')

# Function to start a transcription job with timestamps and diarization
def start_transcription_job(audio_file_uri, job_name, language_code='en-US'):
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': audio_file_uri},
        MediaFormat='mp3',  # Adjust if using a different format
        LanguageCode=language_code,
        Settings={
            'ShowSpeakerLabels': True,  # Enable speaker diarization
            'MaxSpeakerLabels': 2  # Adjust based on expected number of speakers
        }
    )

# Function to get the full JSON transcript from the completed job
def get_transcript_json(job_name):
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Not ready yet...")
        time.sleep(5)
    
    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        response = requests.get(transcript_url)
        return response.json()  # Return the full JSON response
    else:
        raise Exception("Transcription failed")

# Function to delete a transcription job
def delete_transcription_job(job_name):
    try:
        transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        print(f"Transcription job '{job_name}' deleted successfully.")
    except Exception as e:
        print(f"Failed to delete transcription job '{job_name}': {e}")

# Function to save the full JSON response and the transcript with speaker labels
def save_transcript(json_data, full_json_path, transcript_json_path, transcript_with_speakers_path):
    # Extract just the transcript portion
    transcript = json_data['results']['transcripts'][0]['transcript']

    # Process and save the transcript with speaker labels
    items = json_data['results']['items']
    transcript_with_speakers = []

    current_speaker = None
    for item in items:
        if 'start_time' in item and 'end_time' in item:
            start_time = item['start_time']
            end_time = item['end_time']
            speaker_label = item.get('speaker_label', 'Speaker Unknown')
            content = item['alternatives'][0]['content']

            if current_speaker != speaker_label:
                current_speaker = speaker_label
                transcript_with_speakers.append({
                    'speaker': speaker_label,
                    'start_time': start_time,
                    'end_time': end_time,
                    'content': content
                })
            else:
                # Append content to the last segment of the same speaker
                transcript_with_speakers[-1]['content'] += ' ' + content
                transcript_with_speakers[-1]['end_time'] = end_time

    # Save the transcript with speaker labels
    with open(transcript_with_speakers_path, 'w') as f:
        json.dump(transcript_with_speakers, f, indent=4)

# Main function to transcribe audio, save transcripts, and delete the job
def transcribe_audio_to_text_and_cleanup(audio_file_uri, job_name, full_json_path, transcript_json_path, transcript_with_speakers_path):
    start_transcription_job(audio_file_uri, job_name)
    transcript_json = get_transcript_json(job_name)
    save_transcript(transcript_json, full_json_path, transcript_json_path, transcript_with_speakers_path)
    delete_transcription_job(job_name)

# Example usage
audio_file_uri = 's3://YOUR_BUCKET_NAME/podcast-data/84A28157-6FCD-4277-A2C2-9EF1B95C64DD.mp3'
job_name = 'PodcastTranscribe2'
full_json_path = 'full_transcript.json'
transcript_json_path = 'transcript.json'
transcript_with_speakers_path = 'transcript_with_speakers.json'

transcribe_audio_to_text_and_cleanup(audio_file_uri, job_name, full_json_path, transcript_json_path, transcript_with_speakers_path)