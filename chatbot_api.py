from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import io

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_crop_image(image_path):
    # Read the image
    img = cv2.imread(image_path)
    
    # Convert to HSV color space
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Simple analysis based on color
    # These are example thresholds - you would need to adjust these
    green_lower = np.array([25, 40, 40])
    green_upper = np.array([85, 255, 255])
    
    # Create mask for green color
    mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Calculate percentage of green
    green_percentage = (np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])) * 100
    
    # Basic analysis
    if green_percentage > 60:
        health = "healthy"
    elif green_percentage > 30:
        health = "moderate health concerns"
    else:
        health = "potential health issues"
    
    # Example response - in a real system, you'd want more sophisticated analysis
    response = {
        "crop_health": health,
        "green_coverage": f"{green_percentage:.1f}%",
        "recommendations": []
    }
    
    if health == "healthy":
        response["recommendations"].append("Crop appears healthy. Continue current care routine.")
    elif health == "moderate health concerns":
        response["recommendations"].extend([
            "Consider increasing irrigation",
            "Check for pest infestation",
            "Soil nutrient test recommended"
        ])
    else:
        response["recommendations"].extend([
            "Immediate attention required",
            "Check for disease symptoms",
            "Consider consulting an agricultural expert",
            "Soil and plant tissue testing recommended"
        ])
    
    return response

user_sessions = {}

responses = {
    "where is my order": "Aapka order process ho raha hai. 5-7 working day mein deliver ho jaayega.",
    "order kaha hai": "Aapka order 5-7 din mein aayega.",
    "order": "Aap order ka status puchhna chahte hain ya naya product order karna chahte hain?",
    "order status": "Apna Order ID dein, main check karta hoon.",
    "new order": "Main aapko naya product order karne mein madad karta hoon.",
    "hi": "Namaste! Kaise madad kar sakta hoon?",
    "Hi": "Namaste! Kaise madad kar sakta hoon?",
    "hii": "Namaste! Kaise madad kar sakta hoon?",
    "Hii": "Namaste! Kaise madad kar sakta hoon?",
    "Hello": "Namaste! Kaise madad kar sakta hoon?",
    "hello": "Namaskar! Bataiye kya madad chahiye?",
    "hey": "Namaste! Kaise madad kar sakta hoon?",
    "Hey": "Namaste! Kaise madad kar sakta hoon?",
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
    "Acha": "Hnji",
    "bye": "Behtar Zindagi se judne ke liye dhanyavaad! 🙏",
    "exit": "Behtar Zindagi se judne ke liye dhanyavaad! 🙏"
}

def generate_response(user_input, session_id):
    user_input_lower = user_input.lower()
    
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "name": user_input,
            "last_intent": None,
            "pending_info": None
        }
        return f"Welcome to Behtar Zindagi Support, {user_input}! How can I help you?"

    user_context = user_sessions[session_id]

    if user_input_lower in ["ok", "exit", "bye"]:
        return "Behtar Zindagi se judne ke liye dhanyavaad! 🙏"

    if user_context["pending_info"] == "need_order_id" and user_input.isdigit():
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        return [
            f"Aapka order ID {user_input} mila. Kripya wait rukhein, status check kar rahe hain...",
            "Aapka order agle 3-4 working days mein pahunch jaayega."
        ]

    elif user_context["pending_info"] == "need_new_address":
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        return f"Aapka naya address '{user_input}' note kar liya gaya hai."

    elif user_context["pending_info"] == "need_complaint":
        user_context["last_intent"] = None
        user_context["pending_info"] = None
        return f"Aapki samasya '{user_input}' register kar li gayi hai."

    if "order status" in user_input_lower:
        user_context["last_intent"] = "order_status"
        user_context["pending_info"] = "need_order_id"
        return "Apna Order ID dein, main check karta hoon."

    elif "change address" in user_input_lower:
        user_context["last_intent"] = "change_address"
        user_context["pending_info"] = "need_new_address"
        return "Kripya naya address likhein."

    elif "complaint" in user_input_lower:
        user_context["last_intent"] = "complaint"
        user_context["pending_info"] = "need_complaint"
        return "Kripya apni samasya likhein."

    elif "refund" in user_input_lower:
        user_context["last_intent"] = "refund"
        user_context["pending_info"] = "need_order_id"
        return "Refund ke liye Order ID batayein."

    if user_input_lower in responses:
        return responses[user_input_lower]

    return "Maafi chahiye, main aapki baat samajh nahi paaya. Kripya dobara try karein."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    session_id = data.get("session_id", "default")

    if not user_input:
        return jsonify({"response": "Kripya koi message bhejein."}), 400

    response = generate_response(user_input, session_id)

    if isinstance(response, list):
        return jsonify({"response": response})
    else:
        return jsonify({"response": [response]})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze the image
        try:
            analysis_result = analyze_crop_image(filepath)
            
            # Clean up - delete the uploaded file after analysis
            os.remove(filepath)
            
            return jsonify({
                "success": True,
                "analysis": analysis_result
            })
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": f"Error analyzing image: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
