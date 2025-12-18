from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timezone, timedelta

def get_local_time():
    """Restituisce l'ora locale italiana (UTC+1)"""
    return datetime.now(timezone.utc) + timedelta(hours=1)
from models import db, User, VMRequest
from proxmox_api import ProxmoxAPI
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Effettua il login per accedere.'

proxmox_api = ProxmoxAPI(
    host=os.getenv('PROXMOX_HOST', '192.168.56.15'),
    user=os.getenv('PROXMOX_USER', 'root@pam'),
    password=os.getenv('PROXMOX_PASSWORD', ''),
    verify_ssl=os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() == 'true'
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Username o password non corretti.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email', '')
        
       
        if not username or not password:
            flash('Compila tutti i campi obbligatori.', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Le password non corrispondono.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('La password deve essere di almeno 6 caratteri.', 'error')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username già esistente. Scegli un altro username.', 'error')
            return render_template('register.html')
        
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email già registrata.', 'error')
                return render_template('register.html')
        
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email if email else None,
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrazione completata con successo! Ora puoi effettuare il login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        requests = VMRequest.query.order_by(VMRequest.created_at.desc()).all()
        pending_requests = VMRequest.query.filter_by(status='pending').count()
        return render_template('admin_dashboard.html', requests=requests, pending_requests=pending_requests)
    else:
        user_requests = VMRequest.query.filter_by(user_id=current_user.id).order_by(VMRequest.created_at.desc()).all()
        return render_template('user_dashboard.html', requests=user_requests)

@app.route('/request_vm', methods=['GET', 'POST'])
@login_required
def request_vm():
    if current_user.is_admin:
        flash('Gli amministratori non possono richiedere container.', 'warning')
        return redirect(url_for('dashboard'))
    
    
    if request.method == 'POST':
        vm_type = request.form.get('vm_type')
        vm_name = request.form.get('vm_name')
        description = request.form.get('description', '')
        
        if not vm_type or not vm_name:
            flash('Compila tutti i campi obbligatori.', 'error')
            return render_template('request_vm.html')
        
        # Verifica che il tipo sia valido
        valid_types = ['bronze', 'silver', 'gold']
        if vm_type not in valid_types:
            flash('Tipo di VM non valido.', 'error')
            return render_template('request_vm.html')
        
        # Crea la richiesta
        vm_request = VMRequest(
            user_id=current_user.id,
            vm_type=vm_type,
            vm_name=vm_name,
            description=description,
            status='pending'
        )
        
        db.session.add(vm_request)
        db.session.commit()
        
        flash('Richiesta container inviata con successo. In attesa di approvazione.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('request_vm.html')

@app.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    if not current_user.is_admin:
        flash('Accesso negato.', 'error')
        return redirect(url_for('dashboard'))
    
    vm_request = VMRequest.query.get_or_404(request_id)
    
    if vm_request.status != 'pending':
        flash('Questa richiesta è già stata processata.', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        vm_configs = {
            'bronze': {
                'template': '3335'
            },
            'silver': {
                'template': '3336'
            },
            'gold': {
                'template': '3337'
            }
        }
        
        config = vm_configs[vm_request.vm_type]
        
        result = proxmox_api.create_vm(
            vm_name=vm_request.vm_name,
            vm_type=vm_request.vm_type,
            template=config['template']
        )
        
        if result['success']:
            vm_request.status = 'approved'
            vm_request.vm_id = result.get('vmid')
            vm_request.approved_by = current_user.id
            vm_request.approved_at = get_local_time()
            
            try:
                nodes = proxmox_api.api.nodes.get()
                node = nodes[0]['node'] if nodes else None
            except:
                node = None
            
            credentials = proxmox_api.generate_credentials(
                vm_request.vm_name,
                node=node,
                vmid=result.get('vmid')
            )
            vm_request.hostname = credentials['hostname']
            ip_address = credentials['ip_address']
            if not ip_address or ip_address == "IP non disponibile" or ip_address.startswith("Verificare"):
                ip_address = None
            vm_request.ip_address = ip_address
            vm_request.username = credentials['username']
            vm_request.password = credentials['password']
            vm_request.ssh_key = ''
            
            db.session.commit()
            
           
            send_credentials(vm_request)
            
            flash(f'Container creato con successo! ID: {result.get("vmid")}', 'success')
        else:
            vm_request.status = 'rejected'
            vm_request.rejected_by = current_user.id
            vm_request.rejected_at = get_local_time()
            vm_request.rejection_reason = "Impossibile creare il container a causa di problemi tecnici. Contattare l'amministratore per maggiori informazioni."
            vm_request.error_message = result.get('error', 'Errore sconosciuto')  
            db.session.commit()
            flash(f'Impossibile creare il container. Richiesta automaticamente rifiutata.', 'error')
    
    except Exception as e:
        vm_request.status = 'rejected'
        vm_request.rejected_by = current_user.id
        vm_request.rejected_at = get_local_time()
        vm_request.rejection_reason = "Impossibile creare il container a causa di problemi tecnici. Contattare l'amministratore per maggiori informazioni."
        vm_request.error_message = str(e)  
        db.session.commit()
        flash(f'Impossibile creare il container. Richiesta automaticamente rifiutata.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    if not current_user.is_admin:
        flash('Accesso negato.', 'error')
        return redirect(url_for('dashboard'))
    
    vm_request = VMRequest.query.get_or_404(request_id)
    
    if vm_request.status != 'pending':
        flash('Questa richiesta è già stata processata.', 'warning')
        return redirect(url_for('dashboard'))
    
    reason = request.form.get('reason', 'Nessuna ragione specificata')
    vm_request.status = 'rejected'
    vm_request.rejected_by = current_user.id
    vm_request.rejected_at = get_local_time()
    vm_request.rejection_reason = reason
    
    db.session.commit()
    flash('Richiesta rifiutata.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/vm_details/<int:request_id>')
@login_required
def vm_details(request_id):
    vm_request = VMRequest.query.get_or_404(request_id)
    
    if not current_user.is_admin and vm_request.user_id != current_user.id:
        flash('Accesso negato.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('vm_details.html', request=vm_request)

@app.route('/refresh_ip/<int:request_id>', methods=['POST'])
@login_required
def refresh_ip(request_id):
    vm_request = VMRequest.query.get_or_404(request_id)
    
    if not current_user.is_admin and vm_request.user_id != current_user.id:
        flash('Accesso negato.', 'error')
        return redirect(url_for('dashboard'))
    
    if not vm_request.vm_id:
        flash('Container non trovato.', 'error')
        return redirect(url_for('vm_details', request_id=request_id))
    
    try:
        nodes = proxmox_api.api.nodes.get()
        node = nodes[0]['node'] if nodes else None
        
        if node:
            ip_address = proxmox_api.refresh_vm_ip(node, vm_request.vm_id)
            if ip_address:
                vm_request.ip_address = ip_address
                db.session.commit()
                flash(f'IP aggiornato: {ip_address}', 'success')
            else:
                flash('Impossibile recuperare l\'IP. Il container potrebbe non essere ancora avviato o l\'agent non è disponibile.', 'warning')
        else:
            flash('Impossibile trovare il nodo ProxMox.', 'error')
    except Exception as e:
        flash(f'Errore nel recupero IP: {str(e)}', 'error')
    
    return redirect(url_for('vm_details', request_id=request_id))

def send_credentials(vm_request):
    """Invia le credenziali all'utente"""
    pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                is_admin=True,
                email='admin@example.com'
            )
            db.session.add(admin)
            db.session.commit()
            print("Utente admin creato: username='admin', password='admin'")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
