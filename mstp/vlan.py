from .mstp import MSTP

class VLAN:
    """VLAN with its own MSTP instance."""
    # The __init__ method MUST be updated to accept the 'bridge_id' argument
    # that is being passed to it from network.py.
    def __init__(self, vlan_id, bridge_id, ports):
        self.vlan_id = vlan_id
        
        # Pass the bridge_id and ports to the MSTP constructor
        self.mstp = MSTP(bridge_id=bridge_id, ports=ports)
        
        self.ports = ports

    def receive_bpdu(self, port, bpdu):
        self.mstp.receive_bpdu(port, bpdu)

    def get_port_states(self):
        return self.mstp.get_port_states() 