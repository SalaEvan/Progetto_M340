"""Utility per rimuovere tutte le VM dal DB tranne quelle con vm_name 'IP' o 'VerificaIP'.

Uso:
    # modalità interattiva (consigliata)
    python scripts/clean_vm_requests.py

    # modalità non interattiva (senza prompt)
    python scripts/clean_vm_requests.py --yes

Lo script mostra prima i conteggi e richiede conferma prima di eseguire la cancellazione.
"""
import argparse
from app import app
from models import db, VMRequest


def main(skip_confirm: bool):
    with app.app_context():
        total = VMRequest.query.count()
        keep_query = VMRequest.query.filter(VMRequest.vm_name.in_(['IP', 'VerificaIP']))
        keep = keep_query.count()
        delete_query = VMRequest.query.filter(~VMRequest.vm_name.in_(['IP', 'VerificaIP']))
        delete_count = delete_query.count()

        print(f"Totale righe VMRequest: {total}")
        print(f"Righe da conservare (vm_name in ['IP','VerificaIP']): {keep}")
        print(f"Righe da cancellare: {delete_count}")

        if delete_count == 0:
            print("Nessuna riga da eliminare. Esco.")
            return

        if not skip_confirm:
            ans = input("Procedere con la cancellazione? [y/N]: ").strip().lower()
            if ans != 'y':
                print("Operazione annullata dall'utente.")
                return

        # Eseguo la cancellazione
        delete_query.delete(synchronize_session=False)
        db.session.commit()
        print(f"Cancellate {delete_count} righe. Operazione completata.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pulisce VMRequest dal DB lasciando solo IP e VerificaIP')
    parser.add_argument('--yes', action='store_true', help='Esegui senza chiedere conferma')
    args = parser.parse_args()
    main(skip_confirm=args.yes)
