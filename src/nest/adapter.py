"""
NEST Adapter for NASDAQ Stock Agent

Manages A2A server lifecycle, registry registration, and integration with NANDA NEST framework.
"""

import logging
import threading
import time
import requests
from typing import Optional, Dict, Any
from python_a2a import run_server

from .config import NESTConfig
from .agent_bridge import StockAgentBridge
from .agent_logic import process_a2a_message_sync

logger = logging.getLogger(__name__)


class NESTAdapter:
    """
    NEST Adapter for managing A2A server lifecycle and registry integration.
    
    Responsibilities:
    - Initialize StockAgentBridge with configuration
    - Start/stop A2A server in background thread
    - Register/deregister with NANDA Registry
    - Monitor server health and status
    """
    
    def __init__(self, config: NESTConfig):
        """
        Initialize NEST adapter with configuration.
        
        Args:
            config: NEST configuration object
        """
        self.config = config
        self.server_thread: Optional[threading.Thread] = None
        self.is_registered = False
        self._running = False
        self._stop_event = threading.Event()
        
        # Create agent bridge
        agent_url = f"{config.nest_public_url}/a2a"
        self.bridge = StockAgentBridge(
            agent_id=config.agent_id,
            agent_url=agent_url,
            agent_logic=process_a2a_message_sync,
            registry_url=config.nest_registry_url
        )
        
        logger.info(f"🤖 [NESTAdapter] Initialized for agent: {config.agent_id}")
    
    async def start_async(self, register: bool = True):
        """
        Start A2A server in background thread.
        
        Args:
            register: Whether to register with NANDA Registry
        """
        try:
            logger.info(f"🚀 [NESTAdapter] Starting A2A server on port {self.config.nest_port}...")
            
            # Register with NANDA Registry if enabled
            if register and self.config.nest_registry_url:
                self._register()
            
            # Start A2A server in background thread
            self._start_server_thread()
            
            logger.info(f"✅ [NESTAdapter] A2A server started successfully")
            
        except Exception as e:
            logger.error(f"❌ [NESTAdapter] Failed to start A2A server: {e}", exc_info=True)
            raise
    
    async def stop_async(self):
        """
        Stop A2A server gracefully.
        """
        try:
            logger.info("🛑 [NESTAdapter] Stopping A2A server...")
            
            # Deregister from NANDA Registry
            if self.is_registered and self.config.nest_registry_url:
                self._deregister()
            
            # Stop server thread
            self._stop_server_thread()
            
            logger.info("✅ [NESTAdapter] A2A server stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ [NESTAdapter] Error stopping A2A server: {e}", exc_info=True)
    
    def _start_server_thread(self):
        """Start A2A server in background thread."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("⚠️ [NESTAdapter] Server thread already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # Create and start server thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            name="NEST-A2A-Server",
            daemon=True
        )
        self.server_thread.start()
        
        # Wait a moment for server to start
        time.sleep(0.5)
        
        logger.info(f"🧵 [NESTAdapter] Server thread started")
    
    def _stop_server_thread(self):
        """Stop A2A server thread."""
        if not self.server_thread or not self.server_thread.is_alive():
            logger.info("ℹ️ [NESTAdapter] Server thread not running")
            return
        
        # Signal thread to stop
        self._running = False
        self._stop_event.set()
        
        # Wait for thread to finish (with timeout)
        self.server_thread.join(timeout=5.0)
        
        if self.server_thread.is_alive():
            logger.warning("⚠️ [NESTAdapter] Server thread did not stop gracefully")
        else:
            logger.info("✅ [NESTAdapter] Server thread stopped")
        
        self.server_thread = None
    
    def _run_server(self):
        """Run A2A server (executed in background thread)."""
        try:
            logger.info(f"🌐 [NESTAdapter] Starting A2A server on {self.config.host}:{self.config.nest_port}")
            
            # Start python_a2a server
            # Note: run_server() is a blocking call
            run_server(
                self.bridge,
                host=self.config.host,
                port=self.config.nest_port
            )
            
        except Exception as e:
            logger.error(f"❌ [NESTAdapter] Server thread error: {e}", exc_info=True)
            self._running = False
    
    def _register(self):
        """
        Register agent with NANDA Registry.
        
        Implements retry logic with exponential backoff.
        """
        if not self.config.nest_registry_url:
            logger.warning("⚠️ [NESTAdapter] No registry URL configured, skipping registration")
            return
        
        max_retries = 3
        retry_delay = 1.0  # Start with 1 second
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"📝 [NESTAdapter] Registering with NANDA Registry (attempt {attempt}/{max_retries})...")
                
                # Prepare registration payload
                registration_data = {
                    "agent_id": self.config.agent_id,
                    "agent_url": f"{self.config.nest_public_url}/a2a",
                    "api_url": self.config.nest_public_url.replace(f":{self.config.nest_port}", ":8000") + "/api/v1",
                    "agent_facts_url": self.config.nest_public_url.replace(f":{self.config.nest_port}", ":8000") + "/api/v1/agent/info"
                }
                
                # POST to registry
                register_url = f"{self.config.nest_registry_url}/register"
                response = requests.post(
                    register_url,
                    json=registration_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.is_registered = True
                    logger.info(f"✅ [NESTAdapter] Successfully registered with NANDA Registry")
                    logger.info(f"🌐 [NESTAdapter] Agent URL: {registration_data['agent_url']}")
                    return
                else:
                    logger.warning(
                        f"⚠️ [NESTAdapter] Registration failed with status {response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                logger.warning(f"⚠️ [NESTAdapter] Registration attempt {attempt} failed: {e}")
            
            # Retry with exponential backoff
            if attempt < max_retries:
                logger.info(f"⏳ [NESTAdapter] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # All retries failed
        logger.warning(
            f"⚠️ [NESTAdapter] Failed to register after {max_retries} attempts. "
            "Agent will continue in standalone mode."
        )
    
    def _deregister(self):
        """
        Deregister agent from NANDA Registry.
        """
        if not self.config.nest_registry_url or not self.is_registered:
            return
        
        try:
            logger.info("📝 [NESTAdapter] Deregistering from NANDA Registry...")
            
            # DELETE from registry
            deregister_url = f"{self.config.nest_registry_url}/agents/{self.config.agent_id}"
            response = requests.delete(deregister_url, timeout=10)
            
            if response.status_code in [200, 204, 404]:
                self.is_registered = False
                logger.info("✅ [NESTAdapter] Successfully deregistered from NANDA Registry")
            else:
                logger.warning(
                    f"⚠️ [NESTAdapter] Deregistration returned status {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            logger.warning(f"⚠️ [NESTAdapter] Deregistration failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get NEST adapter status.
        
        Returns:
            Dict with status information
        """
        return {
            "nest_enabled": True,
            "nest_running": self.is_running(),
            "nest_port": self.config.nest_port,
            "agent_id": self.config.agent_id,
            "registered": self.is_registered,
            "registry_url": self.config.nest_registry_url,
            "public_url": self.config.nest_public_url,
            "server_thread_alive": self.server_thread.is_alive() if self.server_thread else False
        }
    
    def is_running(self) -> bool:
        """
        Check if A2A server is running.
        
        Returns:
            bool: True if server is running
        """
        return self._running and self.server_thread is not None and self.server_thread.is_alive()

