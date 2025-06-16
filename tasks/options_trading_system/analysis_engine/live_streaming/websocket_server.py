#!/usr/bin/env python3
"""
WebSocket Server for Real-time Dashboard Signal Broadcasting

This module provides WebSocket server functionality to broadcast real-time
institutional flow signals from the analysis engine to connected dashboard frontends.

Features:
- Real-time signal broadcasting to multiple dashboard clients
- Connection management and health monitoring
- Signal formatting for dashboard consumption
- Graceful error handling and reconnection support
- Message queuing for reliable delivery
"""

import os
import sys
import json
import logging
import asyncio
import websockets
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Callable
from collections import deque
import queue
import signal

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardWebSocketServer:
    """
    WebSocket server for broadcasting real-time IFD signals to dashboard clients

    Responsibilities:
    - Manage WebSocket connections from dashboard frontends
    - Format and broadcast real-time institutional flow signals
    - Handle client connection/disconnection gracefully
    - Maintain message queues for reliable delivery
    - Provide connection status and health monitoring
    """

    def __init__(self, host='localhost', port=8765, max_clients=10):
        """Initialize WebSocket server

        Args:
            host: Server host address
            port: Server port number
            max_clients: Maximum concurrent client connections
        """
        self.host = host
        self.port = port
        self.max_clients = max_clients

        # Connection management
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_info: Dict[str, Dict[str, Any]] = {}
        self.server = None
        self.is_running = False

        # Message queuing
        self.message_queue = queue.Queue(maxsize=1000)
        self.signal_callbacks: List[Callable] = []

        # Statistics
        self.stats = {
            'connections_total': 0,
            'connections_active': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'server_start_time': None
        }

        # Server thread
        self.server_thread = None
        self.stop_event = asyncio.Event()

        logger.info(f"WebSocket server initialized on {host}:{port}")

    async def register_client(self, websocket, path):
        """Register new client connection"""
        try:
            client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}_{time.time()}"

            # Check connection limit
            if len(self.clients) >= self.max_clients:
                await websocket.close(code=1013, reason="Server at capacity")
                logger.warning(f"Connection rejected - server at capacity: {client_id}")
                return

            # Add client
            self.clients.add(websocket)
            self.client_info[client_id] = {
                'websocket': websocket,
                'connected_at': datetime.now(timezone.utc),
                'messages_sent': 0,
                'last_ping': datetime.now(timezone.utc)
            }

            self.stats['connections_total'] += 1
            self.stats['connections_active'] = len(self.clients)

            logger.info(f"Client connected: {client_id} (Total: {len(self.clients)})")

            # Send welcome message with connection info
            welcome_msg = {
                'type': 'connection',
                'status': 'connected',
                'client_id': client_id,
                'server_time': datetime.now(timezone.utc).isoformat(),
                'message': 'Connected to IFD Live Streaming Server'
            }
            await websocket.send(json.dumps(welcome_msg))

            # Handle client messages
            async for message in websocket:
                await self.handle_client_message(websocket, client_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up client
            await self.unregister_client(websocket, client_id)

    async def unregister_client(self, websocket, client_id):
        """Unregister client connection"""
        try:
            if websocket in self.clients:
                self.clients.remove(websocket)

            if client_id in self.client_info:
                del self.client_info[client_id]

            self.stats['connections_active'] = len(self.clients)
            logger.info(f"Client {client_id} unregistered (Active: {len(self.clients)})")

        except Exception as e:
            logger.error(f"Error unregistering client {client_id}: {e}")

    async def handle_client_message(self, websocket, client_id, message):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'ping':
                # Respond to ping with pong
                pong_response = {
                    'type': 'pong',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'client_id': client_id
                }
                await websocket.send(json.dumps(pong_response))

                # Update last ping time
                if client_id in self.client_info:
                    self.client_info[client_id]['last_ping'] = datetime.now(timezone.utc)

            elif msg_type == 'subscribe':
                # Handle subscription to specific signal types
                signal_types = data.get('signal_types', ['all'])
                logger.info(f"Client {client_id} subscribed to: {signal_types}")

                # Store subscription preferences
                if client_id in self.client_info:
                    self.client_info[client_id]['subscriptions'] = signal_types

                # Send confirmation
                confirm_msg = {
                    'type': 'subscription_confirmed',
                    'signal_types': signal_types,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                await websocket.send(json.dumps(confirm_msg))

            elif msg_type == 'status_request':
                # Send server status
                status_msg = await self.get_server_status()
                await websocket.send(json.dumps(status_msg))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")

    async def broadcast_signal(self, signal_data):
        """Broadcast institutional flow signal to all connected clients"""
        if not self.clients:
            return

        # Format signal for dashboard consumption
        formatted_signal = self.format_signal_for_dashboard(signal_data)

        # Broadcast to all clients
        disconnected_clients = []

        for websocket in self.clients.copy():
            try:
                await websocket.send(json.dumps(formatted_signal))
                self.stats['messages_sent'] += 1

                # Update client message count
                client_id = self.get_client_id_by_websocket(websocket)
                if client_id and client_id in self.client_info:
                    self.client_info[client_id]['messages_sent'] += 1

            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.stats['messages_failed'] += 1
                disconnected_clients.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected_clients:
            client_id = self.get_client_id_by_websocket(websocket)
            await self.unregister_client(websocket, client_id)

    def format_signal_for_dashboard(self, signal_data):
        """Format institutional flow signal for dashboard consumption"""
        try:
            # Handle both dict and object signals
            if hasattr(signal_data, 'to_dict'):
                signal_dict = signal_data.to_dict()
            elif isinstance(signal_data, dict):
                signal_dict = signal_data
            else:
                logger.warning(f"Unknown signal format: {type(signal_data)}")
                return None

            # Create dashboard-friendly format
            formatted = {
                'type': 'ifd_signal',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signal': {
                    'strike': signal_dict.get('strike'),
                    'option_type': signal_dict.get('option_type'),
                    'signal_strength': signal_dict.get('signal_strength'),
                    'final_confidence': signal_dict.get('final_confidence'),
                    'action': signal_dict.get('action', 'MONITOR'),
                    'pressure_ratio': signal_dict.get('pressure_ratio'),
                    'total_volume': signal_dict.get('total_volume'),
                    'market_price': signal_dict.get('market_price'),
                    'analysis_time': signal_dict.get('analysis_time', datetime.now(timezone.utc).isoformat())
                },
                'metadata': {
                    'source': 'ifd_v3_live',
                    'latency_ms': signal_dict.get('latency_ms', 0),
                    'signal_id': signal_dict.get('signal_id', f"signal_{int(time.time() * 1000)}")
                }
            }

            return formatted

        except Exception as e:
            logger.error(f"Error formatting signal: {e}")
            return None

    def get_client_id_by_websocket(self, websocket):
        """Get client ID by websocket object"""
        for client_id, info in self.client_info.items():
            if info.get('websocket') == websocket:
                return client_id
        return None

    async def broadcast_status_update(self, status_type, data):
        """Broadcast status update to all clients"""
        status_msg = {
            'type': 'status_update',
            'status_type': status_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }

        for websocket in self.clients.copy():
            try:
                await websocket.send(json.dumps(status_msg))
            except:
                # Client disconnected, will be cleaned up in next broadcast
                pass

    async def get_server_status(self):
        """Get comprehensive server status"""
        uptime = 0
        if self.stats['server_start_time']:
            uptime = (datetime.now(timezone.utc) - self.stats['server_start_time']).total_seconds()

        return {
            'type': 'server_status',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': {
                'running': self.is_running,
                'host': self.host,
                'port': self.port,
                'uptime_seconds': uptime,
                'connections_active': len(self.clients),
                'connections_total': self.stats['connections_total'],
                'messages_sent': self.stats['messages_sent'],
                'messages_failed': self.stats['messages_failed'],
                'max_clients': self.max_clients
            }
        }

    def register_signal_callback(self, callback):
        """Register callback for new signals"""
        self.signal_callbacks.append(callback)

    def start_server(self):
        """Start WebSocket server in background thread"""
        if self.is_running:
            logger.warning("Server already running")
            return

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        time.sleep(1)
        logger.info(f"WebSocket server started on {self.host}:{self.port}")

    def _run_server(self):
        """Run server in asyncio event loop"""
        async def run():
            try:
                self.stats['server_start_time'] = datetime.now(timezone.utc)
                self.is_running = True

                # Start WebSocket server
                self.server = await websockets.serve(
                    self.register_client,
                    self.host,
                    self.port
                )

                logger.info(f"WebSocket server listening on {self.host}:{self.port}")

                # Keep server running
                await self.stop_event.wait()

            except Exception as e:
                logger.error(f"WebSocket server error: {e}")
            finally:
                self.is_running = False

        # Run server
        asyncio.run(run())

    def stop_server(self):
        """Stop WebSocket server"""
        if not self.is_running:
            return

        logger.info("Stopping WebSocket server...")

        # Signal stop (must be called from async context)
        async def stop_async():
            self.stop_event.set()

        try:
            asyncio.run(stop_async())
        except RuntimeError:
            # If already in an event loop, just set the flag
            pass

        # Close server
        if self.server:
            self.server.close()

        # Wait for thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)

        self.is_running = False
        logger.info("WebSocket server stopped")

    def send_signal_sync(self, signal_data):
        """Send signal synchronously (thread-safe)"""
        if not self.is_running or not self.clients:
            return

        # Add signal to queue for async processing
        try:
            self.message_queue.put_nowait({
                'type': 'signal',
                'data': signal_data,
                'timestamp': time.time()
            })

            # Force immediate processing by creating a simple async runner
            def process_immediately():
                async def send_now():
                    if self.clients:
                        await self.broadcast_signal(signal_data)

                try:
                    asyncio.run(send_now())
                except Exception as e:
                    logger.warning(f"Immediate signal sending failed: {e}")

            # Run in background thread to avoid blocking
            threading.Thread(target=process_immediately, daemon=True).start()

        except queue.Full:
            logger.warning("Message queue full, dropping signal")
        except Exception as e:
            logger.error(f"Error sending signal: {e}")

    async def process_message_queue(self):
        """Process queued messages (for future async integration)"""
        while self.is_running:
            try:
                # Check for queued messages
                if not self.message_queue.empty():
                    message = self.message_queue.get_nowait()

                    if message['type'] == 'signal':
                        await self.broadcast_signal(message['data'])

                await asyncio.sleep(0.1)  # Small delay

            except Exception as e:
                logger.error(f"Error processing message queue: {e}")

# Factory function for easy integration
def create_dashboard_websocket_server(host='localhost', port=8765):
    """Create WebSocket server for dashboard integration"""
    return DashboardWebSocketServer(host=host, port=port)

# Integration with StreamingBridge
class WebSocketSignalBroadcaster:
    """Integrates WebSocket server with StreamingBridge for signal broadcasting"""

    def __init__(self, websocket_server: DashboardWebSocketServer):
        self.websocket_server = websocket_server
        self.signals_sent = 0

    def broadcast_signal(self, signal):
        """Broadcast signal to dashboard clients"""
        try:
            # Send signal via WebSocket
            self.websocket_server.send_signal_sync(signal)
            self.signals_sent += 1

            logger.debug(f"Signal broadcasted to dashboard: {signal.strike}{signal.option_type}")

        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}")

    def get_stats(self):
        """Get broadcasting statistics"""
        return {
            'signals_sent': self.signals_sent,
            'active_connections': len(self.websocket_server.clients),
            'server_running': self.websocket_server.is_running
        }

# Example usage and testing
if __name__ == "__main__":
    # Test WebSocket server
    logger.info("Starting WebSocket server test")

    # Create server
    server = create_dashboard_websocket_server()

    # Start server
    server.start_server()

    # Test signal broadcasting
    def test_signal_broadcasting():
        import time
        time.sleep(2)  # Wait for server to start

        # Create test signal
        test_signal = {
            'strike': 22000,
            'option_type': 'C',
            'signal_strength': 'EXTREME',
            'final_confidence': 0.95,
            'action': 'STRONG_BUY',
            'pressure_ratio': 3.2,
            'total_volume': 1500,
            'market_price': 22025.50
        }

        # Send test signals
        for i in range(5):
            test_signal['signal_id'] = f"test_signal_{i}"
            server.send_signal_sync(test_signal)
            time.sleep(1)

    # Start test in background
    test_thread = threading.Thread(target=test_signal_broadcasting, daemon=True)
    test_thread.start()

    # Keep server running
    try:
        logger.info(f"WebSocket server running on ws://localhost:8765")
        logger.info("Connect a WebSocket client to test signal broadcasting")
        logger.info("Press Ctrl+C to stop")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping server...")
        server.stop_server()
        logger.info("Server stopped")
