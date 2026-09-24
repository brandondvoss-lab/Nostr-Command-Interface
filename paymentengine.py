"""
dvm_backend.py
FastAPI backend for Nostr DVM Payment Processing via Coinos.
Handles secure API communication to generate invoices and verify payments.

Dependencies: pip install fastapi uvicorn httpx pydantic
Run with: uvicorn dvm_backend:app --host 127.0.0.1 --port 5000
"""
import asyncio
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="DVM Payment Gateway (Coinos)")

# Allow local frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    amount: int  # in sats
    memo: str = "Nostr DVM Job"
    token: str   # Coinos API Key / JWT

class WaitPaymentRequest(BaseModel):
    invoice_id: Optional[str] = None
    payment_hash: Optional[str] = None
    token: Optional[str] = ""
    timeout: int = 300  # Default to 5 minutes (300 seconds) wait time

COINOS_API_BASE = "https://coinos.io/api"

@app.post("/api/invoice")
async def create_invoice(req: InvoiceRequest):
    """Generates a lightning invoice using the Coinos API."""
    logger.info(f"Generating invoice for {req.amount} sats. Memo: {req.memo}")
    async with httpx.AsyncClient() as client:
        try:
            # Coinos API expects the payload wrapped inside 'invoice'
            payload = {
                "invoice": {
                    "amount": req.amount,
                    "type": "lightning",
                    "description": req.memo
                }
            }
            
            response = await client.post(
                f"{COINOS_API_BASE}/invoice",
                headers={
                    "Authorization": f"Bearer {req.token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15.0
            )
            
            if response.status_code != 200:
                logger.error(f"Coinos Response ({response.status_code}): {response.text}")
                
            response.raise_for_status()
            data = response.json()
            
            # Coinos returns nested invoice details
            inv_data = data.get("invoice", data)
            bolt11 = inv_data.get("lightning") or inv_data.get("text") or inv_data.get("bolt11") or inv_data.get("payment_request")
            payment_hash = inv_data.get("hash") or inv_data.get("id") or data.get("hash")
            
            logger.info(f"Invoice generated successfully. Hash: {payment_hash}")
            return {
                "success": True,
                "bolt11": bolt11,
                "payment_hash": payment_hash
            }
        except httpx.HTTPError as e:
            logger.error(f"Coinos API Error during invoice generation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Coinos API Error: {str(e)}")


@app.get("/api/invoice/status")
async def check_invoice_status(payment_hash: str, token: str):
    """Polls Coinos to see if a specific invoice has been paid."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{COINOS_API_BASE}/lightning/invoice/{payment_hash}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            is_paid = data.get("settled") is True or data.get("status") == "settled"
            return {"paid": is_paid}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Coinos API Error: {str(e)}")


@app.post("/api/invoice/wait")
async def wait_for_payment(req: WaitPaymentRequest):
    """
    Long-polls Coinos to verify payment settlement.
    Prevents the system from failing by instantly checking status. 
    It loops and checks until paid, or until the timeout is reached.
    """
    target_id = req.invoice_id or req.payment_hash
    if not target_id:
        raise HTTPException(status_code=400, detail="Missing required invoice_id or payment_hash.")

    logger.info(f"Starting async payment poll loop for invoice {target_id} (Timeout: {req.timeout}s)")
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < req.timeout:
            try:
                response = await client.get(
                    f"{COINOS_API_BASE}/lightning/invoice/{target_id}",
                    headers={"Authorization": f"Bearer {req.token}"} if req.token else {},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    is_paid = data.get("settled") is True or data.get("status") == "settled"
                    
                    if is_paid:
                        logger.info(f"Payment CONFIRMED settled for invoice: {target_id}")
                        return {
                            "success": True,
                            "paid": True, 
                            "invoice_id": target_id,
                            "payment_hash": target_id
                        }
            except httpx.HTTPError as e:
                logger.warning(f"Polling check error for {target_id}: {str(e)}")
            
            # Sleep for 3 seconds before checking again to avoid hammering the Coinos API
            await asyncio.sleep(3.0)
            
    logger.warning(f"Payment poll timed out after {req.timeout} seconds for invoice: {target_id}")
    return {
        "success": False,
        "paid": False, 
        "invoice_id": target_id,
        "payment_hash": target_id, 
        "message": "Timeout reached without payment settlement."
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)