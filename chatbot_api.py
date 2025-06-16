import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from transformers import WhisperProcessor, WhisperForConditionalGeneration, AutoTokenizer, AutoModelForCausalLM, MarianMTModel, MarianTokenizer, pipeline
import torch
import torchaudio
import base64
import io
import uuid
import scipy.io.wavfile
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:8000"])

# Initialize models
whisper_model_id = "openai/whisper-small"
whisper_processor = WhisperProcessor.from_pretrained(whisper_model_id)
whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_id).to("cuda" if torch.cuda.is_available() else "cpu")
whisper_model.config.forced_decoder_ids = None  # Allow model to infer language

falcon_model_id = "tiiuae/falcon-rw-1b"
falcon_tokenizer = AutoTokenizer.from_pretrained(falcon_model_id)
falcon_model = AutoModelForCausalLM.from_pretrained(
    falcon_model_id,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)

llm_pipe = pipeline(
    "text-generation",
    model=falcon_model,
    tokenizer=falcon_tokenizer,
    max_new_tokens=100,
    do_sample=False,
    temperature=0.5,
    # device="cuda" if torch.cuda.is_available() else "cpu",
    top_k=50,
    repetition_penalty=1.2
)

en_hi_tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-hi")
en_hi_model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-hi")

def translate_en_to_hi(text):
    tokens = en_hi_tokenizer([text], return_tensors="pt", padding=True, truncation=True)
    translated = en_hi_model.generate(**tokens)
    return en_hi_tokenizer.batch_decode(translated, skip_special_tokens=True)[0]

user_sessions = {}

responses = {
    "where is my order": "Aapka order process ho raha hai. 5-7 working day mein deliver ho jaayega.",
    "order kaha hai": "Aapka order 5-7 din mein aayega.",
    "order": "Aap order ka status puchhna chahte hain ya naya product order karna chahte hain?",
    "order status": "Apna Order ID dein, main check karta hoon.",
    "new order": "Main aapko naya product order karne mein madad karta hoon.",
    "hi": "Namaste! Kaise madad kar sakta hoon?",
    "hello": "Namaskar! Bataiye kya madad chahiye?",
    "hey": "Namaste! Kaise madad kar sakta hoon?",
    "order kaha hai mera": "Aapka order 5-7 din mein pahunch jaayega.",
    "i want to know your order id": "Kripya apna Order ID batayein.",
    "do you have any complaint": "Kripya apni samasya detail mein batayein.",
    "call me": "Hamari team aapko jald call karegi.",
    "okk i will checking your order id": "Thik hai, aap check kar lijiye.",
    "wait": "Theek hai, main intezaar karta hoon.",
    "okay thanks": "Koi baat nahi! Aapka din shubh ho!",
    "its pleasure to help you sir": "Aapki madad karke humein khushi hui!",
    "ok": "Behtar Zindagi se judne ke liye dhanyavaad!",
    "mera order kab aayega": "Aapka order 5-7 din mein aapke paas pahunch jaayega.",
    "tracking id chahiye": "Kripya apna Order ID batayein, main aapko Tracking ID dunga.",
    "cancel my order": "Apna Order ID bhejein. Agar possible hai toh hum cancel kar denge.",
    "change delivery address": "Zaroor! Kripya naya address aur Order ID bhejein.",
    "do you have pesticides": "Haan ji, humare paas kai tarah ke pesticide uplabdh hain. Aap kis crop ke liye dekh rahe hain?",
    "what is the best fertilizer for wheat": "Gehu ke liye NPK ya DAP best hota hai. Zaroori ho toh humare expert se baat bhi kar sakte hain.",
    "organic seeds available?": "Haan, alag-alag crops ke organic seeds uplabdh hain. Kripya crop ka naam batayein.",
    "drip irrigation kit available?": "Haan! Har size ke khet ke liye drip irrigation kits uplabdh hain. Price ya detail chahiye?",
    "complaint register karna hai": "Aapka concern note kar liya gaya hai. Kripya detail mein samasya batayein.",
    "issue with payment": "Khed hai! Kripya transaction ID bhejein, hum turant madad karenge.",
    "wrong product delivered": "Maafi chaahte hain! Apna order ID aur galat product ki photo bhejein.",
    "product not received": "Dukh hai sun kar. Order ID batayein, hum turant check karenge.",
    "call me": "Zaroor! Hamara agri support executive aapko 24 ghante ke andar call karega.",
    "talk to human": "Thik hai! Main aapko ek agent se jod raha hoon.",
    "what crop should I plant now": "Apna location aur mahina batayein, hum behtar fasal suggest karenge.",
    "how to increase tomato yield": "Sahi spacing, samay par paani aur balanced khad se production badhega. Pura guide chahiye?",
    "my crop is infected": "Kripya photo bhejein ya issue batayein, humare experts madad karenge.",
    "kya aap soil test karte hain": "Haan, hum soil testing kits aur service dono dete hain. Book karna chahenge?",
    "return policy kya hai": "Product delivery ke 7 din ke andar return possible hai, agar unused ho.",
    "how to request refund": "App ya website se return request raise karke refund le sakte hain. 5-7 din mein process hota hai.",
    "exchange product": "Haan, agar product policy mein fit baithta hai toh exchange ho sakta hai. Shuru karen process?",
    "place same order again": "Bilkul! Apna last order ID ya crop ka naam batayein, hum repeat kar denge.",
    "do you have discount for farmers": "Haan, hum regular discount dete hain. Aap WhatsApp par offers lena chahenge?",
    "what's your loyalty program": "Behtar Zindagi Rewards se har purchase pe points milenge. Jaldi aa raha hai!",
    "thank you": "Aapka dhanyavaad! Ham hamesha aapke kheti ke safar mein saath hain. 🙏",
    "no thank you": "Aapka dhanyavaad! Ham hamesha aapke kheti ke safar mein saath hain.",
    "thik hai": "Theek hai! Aapki kheti safal ho! 🌾",
    "okk": "Kya main aapki kisi aur cheez mein madad kar sakta hoon?",
    "acha": "hnji",
    "bye": "Behtar Zindagi se judne ke liye dhanyavaad! 🙏",
    "exit": "Behtar Zindagi se judne ke liye dhanyavaad! 🙏"
}

def generate_response(user_input, session_id):
    user_input_lower = user_input.lower().strip()
    logger.info(f"Processing user input: {user_input_lower}")

    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "name": user_input,
            "last_intent": None,
            "pending_info": None
        }
        logger.info(f"New session created for session_id: {session_id}")
        return f"Welcome to Behtar Zindagi Support, {user_input}! How can I help you?"

    user_context = user_sessions[session_id]

    if user_input_lower in ["ok", "exit", "bye"]:
        logger.info(f"Exiting session for session_id: {session_id}")
        return "Behtar Zindagi se judne ke liye dhanyavaad! 🙏"

    if user_context["pending_info"] == "need_order_id" and user_input.isdigit():
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        logger.info(f"Order ID {user_input} received for session_id: {session_id}")
        return [
            f"Aapka order ID {user_input} mila. Kripya rukhein, status check kar rahe hain...",
            "Aapka order agle 3-4 working days mein pahunch jaayega."
        ]

    elif user_context["pending_info"] == "need_new_address":
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        logger.info(f"New address {user_input} received for session_id: {session_id}")
        return f"Aapka naya address '{user_input}' note kar liya gaya hai."

    elif user_context["pending_info"] == "need_complaint":
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        logger.info(f"Complaint {user_input} registered for session_id: {session_id}")
        return f"Aapki samasya '{user_input}' register kar li gayi hai."

    if "order status" in user_input_lower:
        user_context["last_intent"] = "order_status"
        user_context["pending_info"] = "need_order_id"
        logger.info(f"Order status intent detected for session_id: {session_id}")
        return "Apna Order ID dein, main check karta hoon."

    elif "change address" in user_input_lower:
        user_context["last_intent"] = "change_address"
        user_context["pending_info"] = "need_new_address"
        logger.info(f"Change address intent detected for session_id: {session_id}")
        return "Kripya naya address likhein."

    elif "complaint" in user_input_lower:
        user_context["last_intent"] = "complaint"
        user_context["pending_info"] = "need_complaint"
        logger.info(f"Complaint intent detected for session_id: {session_id}")
        return "Kripya apni samasya likhein."

    elif "refund" in user_input_lower:
        user_context["last_intent"] = "refund"
        user_context["pending_info"] = "need_order_id"
        logger.info(f"Refund intent detected for session_id: {session_id}")
        return "Refund ke liye Order ID batayein."

    if user_input_lower in responses:
        logger.info(f"Matched predefined response for input: {user_input_lower}")
        return responses[user_input_lower]

    logger.info(f"Falling back to LLM for input: {user_input_lower}")
    try:
        llm_reply = llm_pipe(user_input)[0]['generated_text']
        return llm_reply
    except Exception as e:
        logger.error(f"LLM error: {str(e)}", exc_info=True)
        return "Kuchh galat ho gaya. Kripya dobara koshish karein."

def call_model_api(user_input, session_id):
    user_input_lower = user_input.lower().strip()
    logger.info(f"Processing user input: {user_input_lower}")
    
    url = "http://192.168.0.3:6969/chat"
    headers = {"Content-Type": "application/json"}
    data = {"user_question": user_input, "user_id": session_id, "product_name" : "fogger"}
    
    try:
        logger.info(f"Making API call to: {url}")
        logger.info(f"Request data: {data}")
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        logger.info(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"API response data: {response_data}")
            
            if "answer" in response_data:
                return response_data
            else:
                logger.error(f"Unexpected response format: {response_data}")
                return "Unexpected response format from external API"
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            return f"External API error: HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error("API call timed out")
        return "External API request timed out. Please try again."
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to external API: {str(e)}")
        return "Unable to connect to external API. Please check the connection."
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error to external API: {str(e)}")
        return f"Error communicating with external API: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in call_model_api: {str(e)}", exc_info=True)
        return "An unexpected error occurred while processing your request."

def validate_wav_file(audio_bytes):
    """Validate if the audio bytes represent a valid WAV file."""
    try:
        with io.BytesIO(audio_bytes) as f:
            sample_rate, data = scipy.io.wavfile.read(f)
        logger.info(f"WAV validation successful: sample_rate={sample_rate}, data_shape={data.shape}")
        return True
    except Exception as e:
        logger.error(f"WAV validation failed: {str(e)}")
        return False

def speech_to_text(audio_data, audio_format=None, is_base64=False):
    try:
        if is_base64:
            if audio_data.startswith("data:audio/wav;base64,"):
                audio_data = audio_data.split(",")[1]
            try:
                audio_bytes = base64.b64decode(audio_data, validate=True)
            except base64.binascii.Error as e:
                logger.error(f"Invalid base64 string: {str(e)}")
                raise Exception(f"Invalid base64 audio data: {str(e)}")

            if audio_format != 'audio/wav':
                logger.error(f"Unsupported audio format: {audio_format}")
                raise Exception(f"Unsupported audio format: {audio_format}. Only audio/wav is supported.")

            if not validate_wav_file(audio_bytes):
                raise Exception("Audio data is not a valid WAV file")

            audio_file = io.BytesIO(audio_bytes)
        else:
            audio_file = audio_data

        waveform, sample_rate = torchaudio.load(audio_file)
        logger.info(f"Loaded audio: sample_rate={sample_rate}, shape={waveform.shape}")

        if sample_rate != 16000:
            logger.info(f"Resampling audio from {sample_rate}Hz to 16000Hz")
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)

        if waveform.shape[0] > 1:  # Convert to mono if stereo
            waveform = waveform.mean(dim=0, keepdim=True)

        input_features = whisper_processor(waveform.squeeze(), sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(whisper_model.device)

        with torch.no_grad():
            predicted_ids = whisper_model.generate(input_features)
        transcription = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        logger.info(f"Transcription: {transcription}")
        return transcription

    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}", exc_info=True)
        raise Exception(f"Error processing audio data: {str(e)}")

@app.route('/chat', methods=['POST'])
def chat():
    logger.info("=== CHAT ENDPOINT CALLED ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request content type: {request.content_type}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Log raw request data
    raw_data = request.get_data(as_text=True)
    logger.info(f"Raw request data: {raw_data}")
    
    # Try to parse JSON with better error handling
    try:
        data = request.get_json(force=True)
        logger.info(f"Parsed JSON data: {data}")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        logger.error(f"Raw data was: {raw_data}")
        return jsonify({"response": "Invalid JSON format in request"}), 400
    
    if not data:
        logger.error("Empty or None JSON data received")
        return jsonify({"response": "Empty JSON data received"}), 400

    session_id = data.get("session_id", str(uuid.uuid4()))
    if not session_id:
        logger.error("Session ID is required")
        return jsonify({"response": "Session ID is required."}), 400

    audio_format = data.get("audio_format", "audio/wav")

    if "audio_data" in data:
        try:
            user_input = speech_to_text(data["audio_data"], audio_format=audio_format, is_base64=True)
            logger.info(f"Transcribed audio: {user_input}")
        except Exception as e:
            logger.error(f"Error in speech_to_text: {str(e)}")
            return jsonify({"response": str(e)}), 400
    elif "user_question" in data:
        user_input = data.get("user_question", "")
        if not user_input:
            logger.error("Empty user question provided")
            return jsonify({"response": "Kripya koi message bhejein."}), 400
    else:
        logger.error("Missing audio_data or message")
        return jsonify({"response": "Either 'message' or 'audio_data' is required."}), 400

    response = call_model_api(user_input, session_id)
    # response = generate_response(user_input, session_id)
    logger.info(f"Response generated: {response}")
    return jsonify({"response": response if isinstance(response, list) else [response]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9696, debug=True)