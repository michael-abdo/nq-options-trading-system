#!/usr/bin/env python3
"""
Tradovate API Explorer - Discover available endpoints and data structures
This script helps explore the Tradovate API to find options-related endpoints
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for utils access
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_config import setup_logging, get_logger

# Set up logging
log_dir, session_id = setup_logging()
logger = get_logger(__name__)

class TradovateAPIExplorer:
    """Explorer for discovering Tradovate API endpoints and data"""
    
    def __init__(self, cid: str, secret: str, demo: bool = True):
        self.cid = cid
        self.secret = secret
        self.demo = demo
        
        # Set base URL based on environment
        self.base_url = "https://demo.tradovateapi.com/v1" if demo else "https://live.tradovateapi.com/v1"
        self.access_token = None
        
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Tradovate API"""
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
                
                # Save full auth response for exploration
                self.save_response("auth_response", data)
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    def get_headers(self) -> Dict:
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def save_response(self, name: str, data: any):
        """Save API response to file for analysis"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, "data", "tradovate_exploration")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"{name}_{timestamp}.json")
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        logger.info(f"💾 Saved {name} to: {filepath}")
    
    def explore_products(self):
        """Explore all available products"""
        logger.info("🔍 Exploring products...")
        
        try:
            # Get all products
            response = requests.get(
                f"{self.base_url}/product/list",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                products = response.json()
                logger.info(f"Found {len(products)} products")
                
                # Filter for NQ-related products
                nq_products = [p for p in products if "NQ" in p.get("name", "")]
                logger.info(f"Found {len(nq_products)} NQ-related products")
                
                # Look for options products
                option_products = [p for p in products if "Option" in p.get("name", "") or 
                                 p.get("productType") == "Option" or
                                 p.get("contractGroupId") == 3]  # Options typically have groupId 3
                
                logger.info(f"Found {len(option_products)} option products")
                
                self.save_response("all_products", products)
                self.save_response("nq_products", nq_products)
                self.save_response("option_products", option_products)
                
                # Print some examples
                for p in nq_products[:5]:
                    logger.info(f"  NQ Product: {p.get('name')} - Type: {p.get('productType')} - ID: {p.get('id')}")
                    
                for p in option_products[:5]:
                    logger.info(f"  Option Product: {p.get('name')} - Type: {p.get('productType')} - ID: {p.get('id')}")
                
                return products
            else:
                logger.error(f"Failed to get products: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error exploring products: {e}")
            
        return []
    
    def explore_contracts_for_product(self, product_id: int, product_name: str):
        """Explore contracts for a specific product"""
        logger.info(f"🔍 Exploring contracts for product {product_name} (ID: {product_id})...")
        
        try:
            # Method 1: Get contracts by product ID
            response = requests.get(
                f"{self.base_url}/contract/ldeps?ids={product_id}",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                contracts = data.get("contracts", [])
                logger.info(f"Found {len(contracts)} contracts via ldeps")
                self.save_response(f"contracts_ldeps_{product_name}", data)
            
            # Method 2: Find contracts by name pattern
            response = requests.get(
                f"{self.base_url}/contract/find?name={product_name}",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                contracts = response.json()
                logger.info(f"Found {len(contracts)} contracts via find")
                self.save_response(f"contracts_find_{product_name}", contracts)
                
                # Print some examples
                for c in contracts[:3]:
                    logger.info(f"  Contract: {c.get('name')} - Expiry: {c.get('expirationDate')}")
                    
        except Exception as e:
            logger.error(f"Error exploring contracts: {e}")
    
    def explore_contract_groups(self):
        """Explore contract groups"""
        logger.info("🔍 Exploring contract groups...")
        
        try:
            response = requests.get(
                f"{self.base_url}/contractGroup/list",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                groups = response.json()
                logger.info(f"Found {len(groups)} contract groups")
                self.save_response("contract_groups", groups)
                
                # Look for options-related groups
                for g in groups:
                    if "Option" in g.get("name", ""):
                        logger.info(f"  Option Group: {g.get('name')} - ID: {g.get('id')}")
                        
        except Exception as e:
            logger.error(f"Error exploring contract groups: {e}")
    
    def explore_exchange_info(self):
        """Explore exchange information"""
        logger.info("🔍 Exploring exchanges...")
        
        try:
            response = requests.get(
                f"{self.base_url}/exchange/list",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                exchanges = response.json()
                logger.info(f"Found {len(exchanges)} exchanges")
                self.save_response("exchanges", exchanges)
                
                # Look for CME (where NQ trades)
                for e in exchanges:
                    if "CME" in e.get("name", ""):
                        logger.info(f"  Exchange: {e.get('name')} - ID: {e.get('id')}")
                        
        except Exception as e:
            logger.error(f"Error exploring exchanges: {e}")
    
    def explore_specific_nq_options(self):
        """Try specific queries for NQ options"""
        logger.info("🔍 Exploring specific NQ option queries...")
        
        # Common option product patterns
        option_patterns = [
            "NQO",      # NQ Options
            "ONQ",      # Options on NQ
            "QNE",      # Possible option code
            "NQ1!",     # Continuous contract
            "NQOPT",    # NQ Options
            "@NQ"       # Alternative format
        ]
        
        for pattern in option_patterns:
            try:
                response = requests.get(
                    f"{self.base_url}/product/find?name={pattern}",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        logger.info(f"✅ Found {len(products)} products for pattern '{pattern}'")
                        self.save_response(f"products_{pattern}", products)
                        
                        # Get contracts for first product
                        if products:
                            self.explore_contracts_for_product(products[0].get("id"), pattern)
                            
            except Exception as e:
                logger.error(f"Error searching for {pattern}: {e}")
    
    def explore_all(self):
        """Run all exploration methods"""
        logger.info("🚀 Starting comprehensive API exploration...")
        
        # 1. Explore all products
        products = self.explore_products()
        
        # 2. Explore contract groups
        self.explore_contract_groups()
        
        # 3. Explore exchanges
        self.explore_exchange_info()
        
        # 4. Try specific NQ option queries
        self.explore_specific_nq_options()
        
        # 5. Explore NQ futures to understand structure
        logger.info("🔍 Exploring NQ futures structure...")
        try:
            response = requests.get(
                f"{self.base_url}/contract/find?name=NQ",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                nq_contracts = response.json()
                self.save_response("nq_futures_contracts", nq_contracts)
                
                if nq_contracts:
                    # Get details on first contract
                    contract_id = nq_contracts[0].get("id")
                    
                    # Get contract specifications
                    response = requests.get(
                        f"{self.base_url}/contract/item?id={contract_id}",
                        headers=self.get_headers()
                    )
                    
                    if response.status_code == 200:
                        contract_details = response.json()
                        self.save_response("nq_contract_details", contract_details)
                        
                    # Get related contracts
                    response = requests.get(
                        f"{self.base_url}/contract/deps?masterid={contract_id}",
                        headers=self.get_headers()
                    )
                    
                    if response.status_code == 200:
                        related = response.json()
                        self.save_response("nq_related_contracts", related)
                        
        except Exception as e:
            logger.error(f"Error exploring NQ structure: {e}")
        
        logger.info("✅ API exploration complete! Check data/tradovate_exploration/ for results")


def main():
    """Main execution function"""
    # Configuration
    CID = "6540"
    SECRET = "f7a2b8f5-8348-424f-8ffa-047ab7502b7c"
    
    # You'll need to provide these
    print("Tradovate API Explorer")
    print("="*50)
    USERNAME = input("Enter Tradovate username: ")
    PASSWORD = input("Enter Tradovate password: ")
    
    try:
        # Create explorer
        explorer = TradovateAPIExplorer(cid=CID, secret=SECRET, demo=True)
        
        # Authenticate
        if not explorer.authenticate(USERNAME, PASSWORD):
            logger.error("Authentication failed!")
            return
        
        # Run exploration
        explorer.explore_all()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")


if __name__ == "__main__":
    main()