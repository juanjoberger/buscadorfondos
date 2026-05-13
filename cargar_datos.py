from app import app, db, Fondo
import json
import os

def poblar_base_de_datos():
    # En Flask, necesitamos este "contexto" para poder modificar la base de datos desde un script externo
    with app.app_context():
        # Buscamos la ruta exacta del archivo fondos.json
        ruta_json = os.path.join(os.path.dirname(__file__), 'fondos.json')
        
        try:
            # Abrimos y leemos el archivo JSON
            with open(ruta_json, 'r', encoding='utf-8') as archivo:
                fondos_data = json.load(archivo)
                
                agregados = 0
                
                for f in fondos_data:
                    # Verificamos si el fondo ya existe (buscando por nombre) para evitar duplicados
                    existe = Fondo.query.filter_by(nombre=f['nombre']).first()
                    
                    if not existe:
                        # Si no existe, preparamos el nuevo registro para la base de datos
                        nuevo_fondo = Fondo(
                            nombre=f['nombre'],
                            perfil=f['perfil'],
                            pais=f['pais'],
                            region=f['region'],
                            comuna=f['comuna'],
                            link=f['link']
                        )
                        db.session.add(nuevo_fondo)
                        agregados += 1
                
                # Guardamos los cambios definitivamente en la base de datos
                db.session.commit()
                print(f"¡Éxito! Se han agregado {agregados} fondos nuevos a la base de datos.")
                
        except FileNotFoundError:
            print("Error: No se encontró el archivo fondos.json. Asegúrate de que esté en la misma carpeta.")

if __name__ == '__main__':
    poblar_base_de_datos()
