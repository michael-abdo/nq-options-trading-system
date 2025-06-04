#!/usr/bin/env python3
"""
Tradovate Options Chain Client for NQ
Connects to Tradovate API to retrieve full options chain data
"""

import json
import requests
import websocket
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add parent directory to path for utils access
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_config import setup_logging, get_logger

# Set up logging
log_dir, session_id = setup_logging()
logger = get_logger(__name__)
data_logger = get_logger(f"{__name__}.data")

class TradovateOptionsClient:
    """Client for connecting to Tradovate API and retrieving options data"""
    
    def __init__(self, cid: str, secret: str, demo: bool = True):
        """
        Initialize Tradovate client
        
        Args:
            cid: Client ID (app ID)
            secret: Client secret
            demo: Use demo environment (default True)
        """
        self.cid = cid
        self.secret = secret
        self.demo = demo
        
        # Set base URLs based on environment
        if demo:
            self.base_url = "https://demo.tradovateapi.com/v1"
            self.ws_url = "wss://demo.tradovateapi.com/v1/websocket"
            self.md_ws_url = "wss://md-demo.tradovateapi.com/v1/websocket"
        else:
            self.base_url = "https://live.tradovateapi.com/v1"
            self.ws_url = "wss://live.tradovateapi.com/v1/websocket"
            self.md_ws_url = "wss://md.tradovateapi.com/v1/websocket"
        
        self.access_token = None
        self.ws = None
        self.md_ws = None
        self.ws_connected = False
        self.request_id = 0
        
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Tradovate API
        
        Args:
            username: Tradovate username
            password: Tradovate password
            
        Returns:
            bool: True if authentication successful
        """
        logger.info("🔐 Authenticating with Tradovate API...")
        
        auth_data = {
            "name": username,
            "password": password,
            "appId": self.cid,
            "appKey": self.secret,
            "cid": int(self.cid),
            "sec": self.secret
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/accesstokenrequest",
                json=auth_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                self.user_id = data.get("userId")
                logger.info(f"✅ Authentication successful! User ID: {self.user_id}")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    def get_nq_contract_info(self) -> Optional[Dict]:
        """Get NQ futures contract information"""
        logger.info("📊 Fetching NQ contract information...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Search for NQ contracts
            response = requests.get(
                f"{self.base_url}/contract/find?name=NQ",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                data_logger.info(f"Found {len(data)} NQ contracts")
                
                # Find the front month contract
                for contract in data:
                    if contract.get("isFront", False):
                        data_logger.info(f"Front month NQ: {contract.get('name')} - ID: {contract.get('id')}")
                        return contract
                
                # If no front month, return first active
                if data:
                    return data[0]
            else:
                logger.error(f"❌ Failed to get contracts: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error fetching contracts: {e}")
            
        return None
    
    def get_contract_maturities(self, product_id: int) -> List[Dict]:
        """Get all contract maturities for a product"""
        logger.info(f"📅 Fetching contract maturities for product {product_id}...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/contractMaturity/deps?masterid={product_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                maturities = data.get("contractMaturities", [])
                data_logger.info(f"Found {len(maturities)} contract maturities")
                return maturities
            else:
                logger.error(f"❌ Failed to get maturities: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error fetching maturities: {e}")
            
        return []
    
    def get_option_contracts(self, underlying_id: int) -> List[Dict]:
        """Get option contracts for an underlying"""
        logger.info(f"🔍 Searching for option contracts on underlying {underlying_id}...")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        options = []
        
        try:
            # Try to find options based on underlying contract
            # First, get the product info
            response = requests.get(
                f"{self.base_url}/contract/item?id={underlying_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                contract = response.json()
                product_id = contract.get("productId")
                
                # Search for related option products
                response = requests.get(
                    f"{self.base_url}/product/find?name=NQ",
                    headers=headers
                )
                
                if response.status_code == 200:
                    products = response.json()
                    
                    for product in products:
                        # Look for option products (usually contain "Option" in name)
                        if "Option" in product.get("name", "") or product.get("productType") == "Option":
                            option_product_id = product.get("id")
                            data_logger.info(f"Found option product: {product.get('name')} - ID: {option_product_id}")
                            
                            # Get contracts for this option product
                            option_response = requests.get(
                                f"{self.base_url}/contract/ldeps?ids={option_product_id}",
                                headers=headers
                            )
                            
                            if option_response.status_code == 200:
                                option_data = option_response.json()
                                option_contracts = option_data.get("contracts", [])
                                options.extend(option_contracts)
                
                data_logger.info(f"Found {len(options)} option contracts")
                
        except Exception as e:
            logger.error(f"❌ Error fetching option contracts: {e}")
        
        return options
    
    def get_option_chain(self, symbol: str = "NQ") -> Dict:
        """
        Get full option chain for NQ
        
        Returns:
            Dict containing option chain data
        """
        logger.info(f"📊 Fetching option chain for {symbol}...")
        
        # Get the underlying contract first
        nq_contract = self.get_nq_contract_info()
        if not nq_contract:
            logger.error("❌ Could not find NQ contract")
            return {}
        
        underlying_id = nq_contract.get("id")
        underlying_name = nq_contract.get("name")
        
        # Get option contracts
        options = self.get_option_contracts(underlying_id)
        
        # Organize option chain
        chain = {
            "underlying": {
                "symbol": underlying_name,
                "contractId": underlying_id,
                "productId": nq_contract.get("productId")
            },
            "options": [],
            "expirations": set(),
            "strikes": set()
        }
        
        # Process options
        for option in options:
            option_data = {
                "contractId": option.get("id"),
                "symbol": option.get("name"),
                "strike": option.get("strike"),
                "expiration": option.get("expirationDate"),
                "optionType": "Call" if "C" in option.get("name", "") else "Put",
                "productId": option.get("productId")
            }
            
            chain["options"].append(option_data)
            
            if option.get("strike"):
                chain["strikes"].add(option.get("strike"))
            if option.get("expirationDate"):
                chain["expirations"].add(option.get("expirationDate"))
        
        # Convert sets to sorted lists
        chain["strikes"] = sorted(list(chain["strikes"]))
        chain["expirations"] = sorted(list(chain["expirations"]))
        
        logger.info(f"✅ Option chain retrieved: {len(chain['options'])} options, "
                   f"{len(chain['strikes'])} strikes, {len(chain['expirations'])} expirations")
        
        return chain
    
    def connect_websocket(self):
        """Connect to Tradovate WebSocket for real-time data"""
        logger.info("🔌 Connecting to WebSocket...")
        
        def on_open(ws):
            logger.info("✅ WebSocket connected!")
            self.ws_connected = True
            
            # Send authorization
            auth_msg = f"authorize\n1\n\n{self.access_token}"
            ws.send(auth_msg)
            
        def on_message(ws, message):
            # Parse Tradovate WebSocket format
            if message.startswith("o"):
                logger.info("WebSocket open frame received")
            elif message.startswith("h"):
                logger.debug("Heartbeat received")
            elif message.startswith("a"):
                # Array of JSON data
                try:
                    data = json.loads(message[1:])
                    data_logger.debug(f"WebSocket data: {data}")
                except:
                    pass
                    
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket closed")
            self.ws_connected = False
            
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run in separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
    def save_option_chain(self, chain: Dict, filename: Optional[str] = None):
        """Save option chain data to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nq_options_chain_{timestamp}.json"
            
        # Create output directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, "data", "tradovate_options")
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(chain, f, indent=2, default=str)
            
        logger.info(f"💾 Option chain saved to: {filepath}")
        return filepath


def main():
    """Main execution function"""
    # Configuration
    CID = "6540"
    SECRET = "f7a2b8f5-8348-424f-8ffa-047ab7502b7c"
    
    # You'll need to provide these
    USERNAME = input("Enter Tradovate username: ")
    PASSWORD = input("Enter Tradovate password: ")
    
    try:
        # Create client
        client = TradovateOptionsClient(cid=CID, secret=SECRET, demo=True)
        
        # Authenticate
        if not client.authenticate(USERNAME, PASSWORD):
            logger.error("Authentication failed!")
            return
        
        # Get option chain
        chain = client.get_option_chain("NQ")
        
        if chain and chain.get("options"):
            # Save the data
            filepath = client.save_option_chain(chain)
            
            # Print summary
            print("\n" + "="*80)
            print(f"NQ OPTIONS CHAIN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            print(f"Underlying: {chain['underlying']['symbol']}")
            print(f"Total Options: {len(chain['options'])}")
            print(f"Expirations: {len(chain['expirations'])}")
            print(f"Strikes: {len(chain['strikes'])}")
            print(f"\nData saved to: {filepath}")
            print("="*80)
            
            # Connect WebSocket for real-time updates (optional)
            # client.connect_websocket()
            # time.sleep(5)  # Keep connection open
            
        else:
            logger.warning("⚠️ No option chain data retrieved")
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")


if __name__ == "__main__":
    main()