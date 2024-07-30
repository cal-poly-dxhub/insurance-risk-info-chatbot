import json
import boto3
import requests
import time

def transcribe_audio(job_name, file_uri, language_code='en-US'):
    transcribe = boto3.client('transcribe')
    
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        MediaFormat='mp3',  # Adjust this based on your audio file format
        LanguageCode=language_code,
        Settings={'ShowSpeakerLabels': True, 'MaxSpeakerLabels': 2}
    )

    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(1)  # Wait for 5 seconds before checking again

    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        response = requests.get(status['TranscriptionJob']['Transcript']['TranscriptFileUri'])
        transcript = json.loads(response.text)
        
        # Delete the transcription job
        transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        print(f"Transcription job {job_name} deleted.")
        
        return transcript
    
    print(f"Transcription job {job_name} failed.")
    return None

def process_transcript(transcript):
    result = []
    current_speaker = None
    current_segment = None

    for item in transcript['results']['items']:
        if 'speaker_label' in item and 'start_time' in item and 'end_time' in item:
            speaker = item['speaker_label']
            
            if speaker != current_speaker:
                if current_segment:
                    result.append(current_segment)
                
                current_speaker = speaker
                current_segment = {
                    "speaker": speaker,
                    "start_time": item['start_time'],
                    "end_time": item['end_time'],
                    "content": item['alternatives'][0]['content'],
                    "word_timings": []
                }
            else:
                current_segment['end_time'] = item['end_time']
                current_segment['content'] += ' ' + item['alternatives'][0]['content']

            current_segment['word_timings'].append({
                "word": item['alternatives'][0]['content'],
                "start_time": item['start_time'],
                "end_time": item['end_time'],
                "speaker": speaker
            })
        elif current_segment:
            # Handle punctuation or other items without timing information
            current_segment['content'] += item['alternatives'][0]['content']

    if current_segment:
        result.append(current_segment)

    return result

file_uri = 's3://YOUR_BUCKET_NAME/podcast-data/84A28157-6FCD-4277-A2C2-9EF1B95C64DD.mp3'
job_name = 'PodcastTranscrib5'

transcript = transcribe_audio(job_name, file_uri)

if transcript:
    processed_transcript = process_transcript(transcript)
    
    with open('output.json', 'w') as f:
        json.dump(processed_transcript, f, indent=4)
    
    print("Transcription completed and saved to output.json")
else:
    print("Transcription failed")