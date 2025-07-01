import os
import tempfile
import dotenv

def setup_environment():
    """
    Determines the available device (GPU/CPU).
    Returns the device string.
    """
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    return device

def load_tts_model(model_name, device):
    """
    Loads the TTS model to the specified device.
    Returns the loaded TTS object.
    """
    from TTS.api import TTS

    try:
        tts_model = TTS(model_name=model_name).to(device)
        print(f"Model '{model_name}' loaded successfully.")
        return tts_model
    except Exception as e:
        print(f"Error loading model '{model_name}': {e}")
        print("Please ensure you have enough disk space, a stable internet connection, and compatible dependencies.")
        print("Refer to Coqui TTS documentation for troubleshooting model loading issues.")
        exit() # Critical error, cannot proceed without a loaded model

def process_single_file(file_name, file_contents: str, tts_model, output_base_dir="tmp_audio"):
    """
    Processes a single text file: reads it, splits into sentences,
    and synthesizes all sentences into a single combined audio file.
    """
    from nltk.tokenize import sent_tokenize
    import numpy as np
    from scipy.io import wavfile

    # Split the text into sentences using NLTK
    sentences = sent_tokenize(file_contents)
    sentences = [s.strip() for s in sentences if s.strip()] # Clean and filter empty sentences

    if not sentences:
        print(f"No sentences found in file {file_name} after splitting. Skipping.")
        return

    print(f"Found {len(sentences)} sentences in file.")

    # Create output directory if it doesn't exist
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Generate audio for each sentence and combine them
    combined_audio = []
    sample_rate = None
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for i, sentence in enumerate(sentences):
            temp_audio_path = os.path.join(temp_dir, f"temp_sentence_{i}.wav")
            print(f"Synthesizing sentence {i+1}/{len(sentences)}...")
            
            try:
                tts_model.tts_to_file(text=sentence, file_path=temp_audio_path)
                
                # Read the generated audio file
                sr, audio_data = wavfile.read(temp_audio_path)
                if sample_rate is None:
                    sample_rate = sr
                elif sample_rate != sr:
                    print(f"Warning: Sample rate mismatch in sentence {i+1}")
                
                # Add the audio data to our combined array
                combined_audio.append(audio_data)
                
            except Exception as e:
                print(f"Error synthesizing sentence {i+1} from file {file_name}: {e}")
                continue
    
    if combined_audio:
        # Concatenate all audio segments
        final_audio = np.concatenate(combined_audio)
        
        # Save the combined audio file
        output_path = os.path.join(output_base_dir, f"{file_name}_combined.wav")
        wavfile.write(output_path, sample_rate, final_audio)
        print(f"Combined audio saved to: {output_path}")
    else:
        print(f"No audio was generated for file {file_name}")

def convert_file_to_audio(tmp_file_name: str):
    # prepend the temp text file directory to the file name
    tmp_file_path = os.path.join(dotenv.get_key('.env', 'TEMP_TEXT_FILE_DIR'), tmp_file_name)

    with open(tmp_file_path, 'r') as file:
        file_text = file.read()
    device = setup_environment()
    tts_model = load_tts_model("tts_models/multilingual/multi-dataset/xtts_v2", device)
    process_single_file(tmp_file_name, file_text, tts_model)