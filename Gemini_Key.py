import os
import json
import google.generativeai as genai
from google.oauth2 import service_account

class GeminiAIInterface:
    def __init__(self, credentials_path=None):
        # Authentication methods to try
        self.authenticate(credentials_path)

    def authenticate(self, credentials_path=None):
        """
        Attempt to authenticate using multiple methods
        """
        authentication_methods = [
            self.authenticate_from_file,
            self.authenticate_from_env,
            self.authenticate_from_service_account
        ]

        for method in authentication_methods:
            try:
                result = method(credentials_path)
                if result:
                    return
            except Exception as e:
                print(f"Authentication method failed: {method.__name__}")
                print(f"Error: {e}")
        
        raise ValueError("Could not authenticate with Gemini AI")

    def authenticate_from_file(self, credentials_path):
        """
        Try to authenticate using API key from JSON file
        """
        if not credentials_path or not os.path.exists(credentials_path):
            return False

        try:
            with open(credentials_path, 'r') as file:
                creds = json.load(file)
                
                # Try different possible key names
                api_key_candidates = [
                    'api_key', 'apiKey', 'API_KEY', 
                    'key', 'GOOGLE_API_KEY'
                ]
                
                for candidate in api_key_candidates:
                    if candidate in creds:
                        api_key = creds[candidate]
                        genai.configure(api_key=api_key)
                        self.model = genai.GenerativeModel('gemini-pro')
                        return True
            
            return False
        except Exception as e:
            print(f"Error reading credentials file: {e}")
            return False

    def authenticate_from_env(self, _):
        """
        Try to authenticate using environment variable
        """
        api_key = os.environ.get('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            return True
        return False

    def authenticate_from_service_account(self, credentials_path):
        """
        Try to authenticate using service account credentials
        """
        if not credentials_path or not os.path.exists(credentials_path):
            return False

        try:
            # Load service account info
            with open(credentials_path, 'r') as cred_file:
                service_account_info = json.load(cred_file)
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Configure with credentials
            genai.configure(credentials=credentials)
            self.model = genai.GenerativeModel('gemini-pro')
            return True
        except Exception as e:
            print(f"Service account authentication failed: {e}")
            return False

    def generate_response(self, prompt, max_tokens=1000):
        """
        Generate a response from the Gemini AI model
        """
        try:
            response = self.model.generate_content(
                prompt, 
                generation_config={
                    'max_output_tokens': max_tokens
                }
            )
            return response.text
        except Exception as e:
            print(f"Response generation error: {e}")
            return None

    def chat_interactive(self):
        """
        Start an interactive chat session
        """
        print("Gemini AI Chat Interface (type 'exit' to quit)")
        chat = self.model.start_chat(history=[])
        
        while True:
            user_input = input("You: ")
            
            if user_input.lower() == 'exit':
                break
            
            response = chat.send_message(user_input)
            print("Gemini:", response.text)

def main():
    # Potential paths for credentials
    potential_paths = [
        'voltaic-wall-457909-s0-12506e0f4efe.json',
        os.path.expanduser('~/voltaic-wall-457909-s0-12506e0f4efe.json'),
        './credentials.json'
    ]

    # Find first existing path
    credentials_path = next((path for path in potential_paths if os.path.exists(path)), None)

    try:
        # Create Gemini AI interface
        gemini_interface = GeminiAIInterface(credentials_path)
        
        # Example of single prompt generation
        prompt = "Explain quantum computing in simple terms"
        response = gemini_interface.generate_response(prompt)
        print(response)
        
        # Optional: Start interactive chat
        # gemini_interface.chat_interactive()
    
    except Exception as e:
        print(f"Initialization error: {e}")
        print("Please ensure you have:")
        print("1. Enabled Generative Language API in Google Cloud Console")
        print("2. Created valid credentials")
        print("3. Set GOOGLE_API_KEY environment variable or have a valid credentials file")

if __name__ == "__main__":
    main()