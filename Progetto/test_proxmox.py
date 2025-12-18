#!/usr/bin/env python3
"""
Script di test per verificare la connessione a ProxMox
"""

import os
from dotenv import load_dotenv
from proxmox_api import ProxmoxAPI

load_dotenv()

def test_proxmox_connection():
    """Testa la connessione a ProxMox"""
    print("=" * 50)
    print("Test Connessione ProxMox")
    print("=" * 50)
    
    host = os.getenv('PROXMOX_HOST', '192.168.1.100')
    user = os.getenv('PROXMOX_USER', 'root@pam')
    password = os.getenv('PROXMOX_PASSWORD', '')
    verify_ssl = os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() == 'true'
    
    print(f"Host: {host}")
    print(f"User: {user}")
    print(f"Verify SSL: {verify_ssl}")
    print()
    
    try:
        api = ProxmoxAPI(host, user, password, verify_ssl)
        
        if not api.api:
            print("❌ ERRORE: Impossibile connettersi a ProxMox")
            return False
        
        print("✅ Connessione a ProxMox riuscita!")
        print()
        
        # Test: Lista nodi
        print("Test: Lista nodi...")
        try:
            nodes = api.api.nodes.get()
            print(f"✅ Nodi trovati: {len(nodes)}")
            for node in nodes:
                print(f"   - {node.get('node')} (status: {node.get('status')})")
        except Exception as e:
            print(f"❌ Errore: {e}")
        
        print()
        
        # Test: Lista container
        if nodes:
            node = nodes[0]['node']
            print(f"Test: Lista container sul nodo {node}...")
            try:
                containers = api.api.nodes(node).lxc.get()
                print(f"Container trovati: {len(containers)}")
                for container in containers[:5]:  # Mostra solo i primi 5
                    name = container.get('name', 'N/A')
                    vmid = container.get('vmid', 'N/A')
                    status = container.get('status', 'N/A')
                    is_template = container.get('template', 0)
                    template_mark = " (TEMPLATE)" if is_template else ""
                    print(f"   - {name} (ID: {vmid}, Status: {status}){template_mark}")
                if len(containers) > 5:
                    print(f"   ... e altri {len(containers) - 5} container")
            except Exception as e:
                print(f"Errore: {e}")
        
        print()
        
        # Test: Verifica template
        print("Test: Verifica template richiesti...")
        templates_required = ['bronze-template', 'silver-template', 'gold-template']
        if nodes:
            node = nodes[0]['node']
            for template_name in templates_required:
                template_vmid = api.find_template(template_name, node)
                if template_vmid:
                    print(f"Template '{template_name}' trovato (ID: {template_vmid})")
                else:
                    print(f"Template '{template_name}' NON trovato")
                    print(f"   Crea questo template seguendo le istruzioni in proxmox_configs/")
        
        print()
        print("=" * 50)
        print("Test completato!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_proxmox_connection()
