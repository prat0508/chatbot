# Behtar Zindagi Voice-Enabled Chatbot

A voice-enabled chatbot for agricultural support with speech-to-text functionality using the Ultravox model.

## Features

- **Voice Input**: Click the microphone button to record your voice
- **Speech-to-Text**: Uses the Ultravox model to convert speech to text
- **Text Chat**: Traditional text-based chat interface
- **Image Analysis**: Upload images for crop analysis
- **Multi-language Support**: Hindi and English responses

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Flask Backend

```bash
python chatbot_api.py
```

The server will start on `http://localhost:5000`

### 3. Start the Frontend

In a separate terminal, start a simple HTTP server:

```bash
python -m http.server 8000
```

### 4. Access the Application

Open your browser and go to:
```
http://localhost:8000
```

## How to Use Voice Input

1. **Click the Voice Button**: Click the red microphone button in the chat interface
2. **Allow Microphone Access**: Your browser will ask for microphone permission - allow it
3. **Speak Your Message**: The button will turn red and pulse while recording
4. **Stop Recording**: Click the stop button or wait for auto-stop
5. **Auto-Processing**: The system will automatically transcribe your speech and send the message

## Voice Features

- **Real-time Recording**: Visual feedback during recording
- **Automatic Transcription**: Speech is converted to text using Ultravox model
- **Auto-send**: Transcribed text is automatically sent to the chatbot
- **Error Handling**: Clear error messages if transcription fails

## Technical Details

### Backend (Flask)
- **Ultravox Model**: `fixie-ai/ultravox-v0_5-llama-3_2-1b` for speech-to-text
- **Falcon Model**: `tiiuae/falcon-rw-1b` for text generation
- **Endpoints**:
  - `/chat` - Text chat
  - `/voice-to-text` - Voice transcription
  - `/upload-image` - Image analysis

### Frontend (HTML/JavaScript)
- **MediaRecorder API**: For audio recording
- **Web Audio API**: For audio processing
- **Real-time UI**: Visual feedback for recording status

## Troubleshooting

### Microphone Not Working
- Check browser permissions
- Ensure microphone is not being used by another application
- Try refreshing the page

### Transcription Errors
- Speak clearly and at a normal volume
- Ensure good internet connection
- Check server logs for detailed error messages

### Model Loading Issues
- Ensure sufficient RAM (models require ~4GB)
- Check internet connection for model downloads
- Verify all dependencies are installed correctly

## API Endpoints

### POST /voice-to-text
Convert audio to text using Ultravox model.

**Request:**
```json
{
    "audio_data": "data:audio/wav;base64,..."
}
```

**Response:**
```json
{
    "success": true,
    "transcription": "Hello, how can I help you?"
}
```

### POST /chat
Send text message and get response.

**Request:**
```json
{
    "message": "Hello",
    "session_id": "1234567890"
}
```

**Response:**
```json
{
    "response": ["Namaste! Kaise madad kar sakta hoon?"]
}
```

## Browser Compatibility

- Chrome 66+
- Firefox 60+
- Safari 14.1+
- Edge 79+

## License

This project is for educational and agricultural support purposes. 