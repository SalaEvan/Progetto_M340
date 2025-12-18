from proxmoxer import ProxmoxAPI as ProxmoxAPIClient
import random
import string
import ipaddress
import subprocess

class ProxmoxAPI:
    def __init__(self, host, user, password, verify_ssl=False):
        self.host = host
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.api = None
        self._connect()
    
    def _connect(self):
        try:
            self.api = ProxmoxAPIClient(
                self.host,
                user=self.user,
                password=self.password,
                verify_ssl=self.verify_ssl
            )
        except Exception as e:
            
            pass
    
    def get_available_storage(self, node, storage_type='zfspool'):
        """Ottiene lo storage disponibile per ZFS"""
        try:
            if not self.api:
                self._connect()
            

            storages = self.api.nodes(node).storage.get()
            
            print(f"Storage disponibili sul nodo {node}:")
            for storage in storages:
                storage_name = storage.get('storage', 'N/A')
                storage_type_info = storage.get('type', 'N/A')
                content = storage.get('content', '')
                print(f"  - {storage_name} (tipo: {storage_type_info}, content: {content})")
            

            for storage in storages:
                storage_type_info = storage.get('type', '')
                if storage_type_info == storage_type or storage_type_info == 'zfspool':
                    storage_name = storage.get('storage')
                    print(f"Storage ZFS trovato per tipo: {storage_name} (tipo: {storage_type_info})")
                    return storage_name
            
            for storage in storages:
                storage_name = storage.get('storage', '')
                if storage_name and 'zfs' in storage_name.lower():
                    print(f"Storage ZFS trovato per nome: {storage_name}")
                    return storage_name
            

            for storage in storages:
                storage_name = storage.get('storage', '')
                if storage_name and storage_name.lower() in ['localzfs', 'local-zfs']:
                    print(f"Storage trovato (localzfs): {storage_name}")
                    return storage_name
            

            for storage in storages:
                content = storage.get('content', '')
                if 'rootdir' in content or 'images' in content:
                    storage_name = storage.get('storage')
                    storage_type_info = storage.get('type', '')
                    if storage_type_info in ['dir', 'zfspool', 'lvm', 'lvmthin']:
                        print(f"Storage disponibile per container: {storage_name} (tipo: {storage_type_info})")
                        return storage_name
            
            for storage in storages:
                if storage.get('storage') == 'local':
                    print(f"Usando storage fallback: local")
                    return 'local'
            
            print("⚠️ Nessuno storage adatto trovato!")
            return None
        except Exception as e:
            print(f"Errore nell'ottenere lo storage: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_next_vmid(self):
        try:
            if not self.api:
                self._connect()
            
            cluster = self.api.cluster.nextid.get()
            return int(cluster)
        except Exception as e:
            print(f"Errore nell'ottenere il prossimo VMID: {e}")
            return random.randint(100, 999)
    
    def find_template(self, template_name, node):
        try:
            containers = self.api.nodes(node).lxc.get()
            
            if template_name.isdigit():
                template_id = int(template_name)
                for container in containers:
                    if container.get('vmid') == template_id:
                        vmid = container.get('vmid')
                        name = container.get('name', 'N/A')
                        print(f"Template trovato per ID: {vmid} (Nome: {name})")
                        return vmid
            
            for container in containers:
                name = container.get('name', '')
                vmid = container.get('vmid')
                
                if name and name.lower() == template_name.lower():
                    print(f"Container trovato per nome: {name} (ID: {vmid})")
                    return vmid
                
                if str(vmid) == template_name:
                    print(f"Container trovato per ID: {vmid} (Nome: {name})")
                    return vmid
            
            for container in containers:
                name = container.get('name', '')
                if name and template_name.lower() in name.lower():
                    vmid = container.get('vmid')
                    print(f"Container trovato per corrispondenza parziale: {name} (ID: {vmid})")
                    return vmid
            
            print(f"Template '{template_name}' non trovato")
            return None
        except Exception as e:
            print(f"Errore nella ricerca del template: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_vm(self, vm_name, vm_type, template):
        try:
            if not self.api:
                self._connect()
            
            if not self.api:
                return {'success': False, 'error': 'Impossibile connettersi a ProxMox'}
            
            nodes = self.api.nodes.get()
            if not nodes:
                return {'success': False, 'error': 'Nessun nodo disponibile'}
            
            node = None
            for n in nodes:
                if n.get('node') == 'px1':
                    node = 'px1'
                    break
            
            if not node:
                node = nodes[0]['node']
            
            print(f"Usando nodo: {node}")
            
            vmid = self.get_next_vmid()
            template_vmid = self.find_template(template, node)
            
            if template_vmid:
                clone_success = False
                container_created = False
                try:
                    clone_config = {
                        'newid': vmid,
                        'hostname': vm_name,
                        'full': 1
                    }
                    
                    clone_result = self.api.nodes(node).lxc(template_vmid).clone.post(**clone_config)
                    clone_success = True
                    container_created = True
                    
                    import time
                    time.sleep(3)
                    
                    try:
                        self.api.nodes(node).lxc(vmid).status.start.post()
                        time.sleep(10)
                    except:
                        pass
                    
                    errors = []
                    
                    if errors:
                        print(f"⚠️ Container creato ma con avvisi: {errors}")
                        return {
                            'success': True,
                            'vmid': vmid,
                            'message': f'Container creato con successo dal template {template}. Avvisi: {"; ".join(errors)}'
                        }
                    else:
                        return {
                            'success': True,
                            'vmid': vmid,
                            'message': f'Container creato con successo dal template {template}'
                        }
                except Exception as e:
                    error_msg = str(e)
                    print(f"Errore durante il processo: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    
                    if clone_success or container_created:
                        print(f"Clone riuscito, container {vmid} creato nonostante errori nella configurazione")
                        try:
                            check = self.api.nodes(node).lxc(vmid).status.current.get()
                            print(f"Container {vmid} verificato esistente in ProxMox")
                            return {
                                'success': True,
                                'vmid': vmid,
                                'message': f'Container creato con successo dal template {template}. Errore nella configurazione: {error_msg}'
                            }
                        except:
                            if clone_success:
                                return {
                                    'success': True,
                                    'vmid': vmid,
                                    'message': f'Container creato con successo dal template {template}. Errore nella configurazione: {error_msg}'
                                }
                    
                    return {
                        'success': False,
                        'error': f'Errore nel clonare il template {template}: {error_msg}. Verifica che il template esista e sia accessibile.'
                    }
            else:
                return {
                    'success': False,
                    'error': f'Template "{template}" non trovato. Assicurati che i template ct-temp, ct-temp2, ct-temp3 esistano in ProxMox.'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Errore nella comunicazione con ProxMox: {str(e)}'
            }
    
    def _create_container_from_scratch(self, node, vmid, vm_name, cores, memory, swap, disk, storage_name=None):
        try:
            if not storage_name:
                storage_name = self.get_available_storage(node) or 'local'
            try:
                storage_info = self.api.nodes(node).storage('local').content.get()
                alpine_template = None
                for item in storage_info:
                    if 'alpine' in item.get('volid', '').lower() and item.get('content') == 'vztmpl':
                        alpine_template = item.get('volid')
                        break
                
                if not alpine_template:
                    return {
                        'success': False,
                        'error': 'Template Alpine non trovato. Assicurati che ct-temp esista.'
                    }
            except:
                return {
                    'success': False,
                    'error': 'Impossibile trovare template. Usa il template ct-temp.'
                }
            
            # Configurazione del container Alpine
            config = {
                'vmid': vmid,
                'ostemplate': alpine_template, 
                'hostname': vm_name,
                'cores': cores,
                'memory': memory * 1024,  # Converti MB in KB per LXC
                'swap': swap * 1024,      # Converti MB in KB per LXC
                'rootfs': f'{storage_name}:{disk}',
                'net0': 'name=eth0,bridge=vmbr0,ip=dhcp',
                'password': self._generate_password(),
                'unprivileged': 1
            }
            
            # Crea il container
            result = self.api.nodes(node).lxc.post(**config)
            
            # Avvia il container
            self.api.nodes(node).lxc(vmid).status.start.post()
            
            return {
                'success': True,
                'vmid': vmid,
                'message': f'Container creato da zero con successo'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Errore nella creazione del container: {str(e)}'
            }
    
    def generate_credentials(self, vm_name, node=None, vmid=None):
        username = 'root'
        password = 'Admin00$$'
        hostname = vm_name
        
        ip_address = None
        if node and vmid:
            ip_address = self._get_vm_ip(node, vmid)
        
        return {
            'hostname': hostname,
            'ip_address': ip_address,
            'username': username,
            'password': password,
            'ssh_key': ''
        }
    
    def _generate_password(self, length=12):
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(characters) for _ in range(length))
    
    def _get_vm_ip(self, node, vmid):
        """
        Recupera l'IP del container interrogando le interfacce di rete rilevate da ProxMox.
        Metodo robusto per LXC che non richiede l'agent attivo.
        """
        try:
            if not self.api:
                self._connect()
            
            import time
            
            for attempt in range(15):
                if attempt > 0:
                    time.sleep(2)
                
                try:
                    interfaces = self.api.nodes(node).lxc(vmid).interfaces.get()
                    
                    if interfaces:
                        for iface in interfaces:
                            if iface.get('name') != 'lo':
                                inet = iface.get('inet')
                                if inet:
                                    ip = inet.split('/')[0]
                                    if ip and not ip.startswith('127.'):
                                        return ip
                except Exception as e:
                    try:
                        status = self.api.nodes(node).lxc(vmid).status.current.get()
                    except:
                        pass
                    
            return None
        except Exception as e:
            print(f"Errore critico nel recupero IP per container {vmid}: {e}")
            return None
    
    def refresh_vm_ip(self, node, vmid):
        return self._get_vm_ip(node, vmid)
    
    def _generate_ssh_key(self, vm_name):
        return f"ssh-rsa AAAAB3NzaC1yc2E... (chiave SSH per {vm_name})"
