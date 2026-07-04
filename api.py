"""
QbD Farmacia Magistral - Backend API (Render Compatible)
Flask + TF-IDF (ML1) + K-Means (ML2) + JSON knowledge base
Sin SQL Server, sin pyodbc, sin torch
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
import os
import json
import random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)
CORS(app)

# --- Cargar knowledge_base.json ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, 'knowledge_base.json')

print("[DB] Cargando knowledge_base.json...")
with open(KB_PATH, 'r', encoding='utf-8') as f:
    KB = json.load(f)

usuarios = KB['usuarios']
formulas = KB['formulas']
productos = KB['productos']
sedes = KB['sedes']
medicos = KB['medicos']
clientes = KB['clientes']
ventas_fm = KB['ventas_fm']
ventas_pt = KB['ventas_pt']
tiempos_fm = KB['tiempos_fm']
tiempos_pt = KB['tiempos_pt']

print(f"[DB] Datos cargados: {len(formulas)} formulas, {len(productos)} productos, {len(sedes)} sedes, {len(medicos)} medicos, {len(clientes)} clientes, {len(ventas_fm)+len(ventas_pt)} ventas")

# --- Sinonimos ---
SINONIMOS = {
    "piel": "piel dermatitis crema topica cutanea",
    "hongos": "antimicosis antifungico clotrimazol micosis fungal",
    "tos": "antitusivo dextrometorfano jarabe respiratorio",
    "dolor": "analgesico antiinflamatorio ibuprofeno paracetamol",
    "fiebre": "antipyretico paracetamol temperatura",
    "estomago": "gastritis ulcera reflujo omeprazol gastrico digestion",
    "infeccion": "antibiotico amoxicilina bacteriana bacteriano",
    "alergia": "antihistaminico loratadina rinitis estornudo",
    "antibiotico": "amoxicilina infeccion antibacteriano",
    "crema": "topico pomada unguento dermatologico",
    "medico": "doctor colegiatura receta prescripcion",
    "sede": "ubicacion direccion local sucursal",
    "dolor de cabeza": "paracetamol analgesico migraña cefalea",
    "dolor de muelas": "paracetamol ibuprofeno analgesico dental",
    "dolor de espalda": "ibuprofeno antiinflamatorio muscular",
    "gastritis": "omeprazol acidez estomago reflujo ulcera",
    "reflujo": "omeprazol gastroesofagico acidez gastrica",
    "infeccion urinaria": "amoxicilina antibiotico bacteriano",
    "amigdalitis": "amoxicilina antibiotico infeccion garganta",
    "neumonia": "amoxicilina antibiotico pulmon infeccion respiratoria",
    "rinitis": "loratadina antihistaminico alergia estornudo picazon",
    "urticaria": "loratadina antihistaminico alergia picazon piel",
    "artritis": "ibuprofeno antiinflamatorio inflamacion articulaciones",
    "dolor muscular": "ibuprofeno antiinflamatorio inflamacion",
    "colico": "ibuprofeno antiinflamatorio dolor abdominal",
    "alopecia": "minoxidil crecimiento capilar cabello",
    "caida del cabello": "minoxidil alopecia crecimiento capilar",
    "que medicamento": "producto medicamento formula",
    "que producto": "producto medicamento formula",
    "cuanto cuesta": "precio costo valor",
    "cuanto vale": "precio costo valor",
    "cuanto sale": "precio costo valor",
    "hay stock": "disponible stock unidades",
    "tienen": "disponible stock unidades",
    "direccion": "ubicacion direccion sede",
    "donde": "ubicacion direccion sede",
}

def expandir_consulta(consulta):
    consulta_lower = consulta.lower()
    extras = []
    for clave, valores in SINONIMOS.items():
        if clave in consulta_lower:
            extras.append(valores)
    if extras:
        return consulta + " " + " ".join(extras)
    return consulta

# --- Construir documentos para ML1 (chatbot) ---
def construir_documentos():
    docs = []
    for f in formulas:
        desc = f['DescripcionFM']
        texto = f"Formula magistral {f['CodFormula']}: {desc}. Unidad: {f['UnidadMedidaFM']}. Costo: S/ {f['CostoUnitarioFM']}."
        if "piel" in desc.lower() or "dermatol" in desc.lower():
            texto += " Tratamiento para piel, dermatitis, hidratacion cutanea."
        if "amoxicilina" in desc.lower():
            texto += " Antibiotico para infecciones bacterianas."
        if "tos" in desc.lower():
            texto += " Jarabe antitusivo para aliviar la tos."
        if "clotrimazol" in desc.lower():
            texto += " Crema antifungica para hongos en piel, micosis."
        if "minoxidil" in desc.lower():
            texto += " Tratamiento para alopecia, crecimiento capilar."
        docs.append({"id": f['CodFormula'], "categoria": "Formula Magistral", "titulo": desc, "descripcion": texto, "precio": float(f['CostoUnitarioFM']), "unidad": f['UnidadMedidaFM'], "estado": f['EstadoFM']})
    for p in productos:
        desc = p['DescripcionPT']
        uso = p['DescripcionUso']
        texto = f"Producto {p['CodProducto']}: {desc}. Uso: {uso}. Precio: S/ {p['CostoUnitarioPT']}. Stock: {p['StockPT']}."
        docs.append({"id": p['CodProducto'], "categoria": "Producto Terminado", "titulo": desc, "descripcion": texto, "uso": uso, "precio": float(p['CostoUnitarioPT']), "unidad": p['UnidadMedidaPT'], "stock": p['StockPT'], "estado": p['EstadoPT']})
    for s in sedes:
        docs.append({"id": f"SEDE-{s['SedeKey']}", "categoria": "Sede", "titulo": s['NombreSede'], "descripcion": f"Sede {s['NombreSede']}. Ubicacion: {s['Direccion']}, {s['Ciudad']}, {s['Region']}."})
    for m in medicos:
        docs.append({"id": f"MED-{m['MedicoKey']}", "categoria": "Medico", "titulo": f"Dr(a). {m['NombresM']} {m['ApellidosM']}", "descripcion": f"Medico {m['NombresM']} {m['ApellidosM']}, colegiatura {m['ColegiaturaMedico']}. Estado: {m['EstadoM']}."})
    docs.append({"id": "GEN-001", "categoria": "General", "titulo": "QbD Farmacia", "descripcion": "QbD Farmacia Magistral S.A.C. es una empresa farmaceutica peruana dedicada a formulas magistrales y productos farmaceuticos. Inicio en septiembre 2021 en Juliaca y Puno."})
    docs.append({"id": "GEN-002", "categoria": "General", "titulo": "Mision", "descripcion": "Brindar soluciones farmaceuticas personalizadas con calidad, responsabilidad y compromiso."})
    docs.append({"id": "GEN-003", "categoria": "General", "titulo": "Formula magistral", "descripcion": "Formula magistral es un medicamento elaborado para un paciente segun prescripcion medica."})
    docs.append({"id": "GEN-004", "categoria": "General", "titulo": "Servicios", "descripcion": "Servicios: formulas magistrales, productos farmaceuticos, atencion personalizada, orientacion y seguimiento."})
    docs.append({"id": "GEN-005", "categoria": "General", "titulo": "Horarios", "descripcion": "Atencion de lunes a sabado en sedes de Juliaca y Puno."})
    return docs

# --- Modelo ML1: TF-IDF ---
print("[ML] Cargando modelo chatbot (TF-IDF)...")
documentos = construir_documentos()
textos = [f"{d['titulo']}. {d['descripcion']}" for d in documentos]
modelo_ml = TfidfVectorizer()
embeddings = modelo_ml.fit_transform(textos)
print(f"[ML] Modelo chatbot listo. {len(documentos)} documentos indexados.")

# --- Funciones ML ---
def buscar(consulta, top_k=3):
    expandida = expandir_consulta(consulta)
    emb = modelo_ml.transform([expandida])
    sims = cosine_similarity(emb, embeddings)[0]
    top_idx = sims.argsort()[::-1][:top_k]
    return [{**documentos[i], "similitud": round(float(sims[i]), 4)} for i in top_idx]

def detectar_intencion(consulta):
    consulta_lower = consulta.lower()
    emb_consulta = modelo_ml.transform([consulta])
    preguntas_no_respondables = [
        "cuantos pacientes han sido atendidos", "cuantos clientes tenemos",
        "cuantas ventas hemos hecho", "cuanto hemos vendido",
        "cual es la facturacion", "cuales son las estadisticas",
        "cuantos medicos tenemos", "cuantos doctores hay",
        "cuantas personas han venido", "cuantos atendisteis",
        "cuantos han venido", "cuantos se han atendido",
        "cuantos se atendieron", "cuantos pacientes hay", "cuantos clientes hay",
    ]
    for pregunta in preguntas_no_respondables:
        emb_no = modelo_ml.transform([pregunta])
        sim = cosine_similarity(emb_consulta, emb_no)[0][0]
        if sim > 0.4:
            return "no_respondable"
    textos_intencion = {
        "precio": "Cuanto cuesta el producto? Precio, costo, valor, cuanto vale, cuanto sale, cuanto cuesta",
        "disponibilidad": "Hay disponible el producto? Stock, unidades, quedan, hay en existencia, hay disponible",
        "recomendacion": "Necesito un producto para mi dolencia. Me duele, tengo dolor, que puedo tomar, que me recomienda, necesito algo para",
        "informacion": "Cuentame sobre el producto o servicio. Que es, que ofrecen, informacion, detalles, cuentame",
        "ubicacion": "Donde estan ubicados? Sede, direccion, ubicacion, donde queda, donde estan",
        "medico": "Que medicos recetan formulas magistrales? Medico que receta, doctor que prescribe",
    }
    mejor_intencion = None
    mejor_similitud = 0
    for intencion, texto in textos_intencion.items():
        emb_intencion = modelo_ml.transform([texto])
        sim = cosine_similarity(emb_consulta, emb_intencion)[0][0]
        if sim > mejor_similitud:
            mejor_similitud = sim
            mejor_intencion = intencion
    if mejor_similitud > 0.15:
        return mejor_intencion
    return None

def buscar_respuesta_especifica(consulta):
    consulta_lower = consulta.lower()
    respuesta = None
    for s in sedes:
        nombre_lower = s['NombreSede'].lower()
        if any(palabra in consulta_lower for palabra in nombre_lower.split() if len(palabra) > 3):
            if any(p in consulta_lower for p in ['direccion', 'ubicacion', 'donde', 'queda']):
                respuesta = f"{s['NombreSede']}\nDireccion: {s['Direccion']}\nCiudad: {s['Ciudad']}, {s['Region']}"
                break
    if not respuesta:
        for p in productos:
            nombre_lower = p['DescripcionPT'].lower()
            palabras = [w for w in nombre_lower.split() if len(w) > 3]
            if any(palabra in consulta_lower for palabra in palabras):
                if any(px in consulta_lower for px in ['precio', 'cuesta', 'vale', 'sale', 'costo']):
                    respuesta = f"El precio de {p['DescripcionPT']} es S/ {p['CostoUnitarioPT']:.2f} por {p['UnidadMedidaPT']}."
                    break
                elif any(px in consulta_lower for px in ['stock', 'disponible', 'queda', 'quedan', 'hay']):
                    respuesta = f"El producto {p['DescripcionPT']} tiene {p['StockPT']} unidades en stock."
                    break
                elif any(px in consulta_lower for px in ['uso', 'sirve', 'para que', 'que hace', 'beneficio']):
                    respuesta = f"{p['DescripcionPT']}\nUso: {p['DescripcionUso']}\nPrecio: S/ {p['CostoUnitarioPT']:.2f}"
                    break
    if not respuesta:
        for f in formulas:
            nombre_lower = f['DescripcionFM'].lower()
            palabras = [w for w in nombre_lower.split() if len(w) > 3]
            if any(palabra in consulta_lower for palabra in palabras):
                if any(px in consulta_lower for px in ['precio', 'cuesta', 'vale', 'sale', 'costo']):
                    respuesta = f"La formula magistral {f['DescripcionFM']} cuesta S/ {f['CostoUnitarioFM']:.2f} por {f['UnidadMedidaFM']}."
                    break
    return respuesta

def buscar_info_tabla(consulta):
    consulta_lower = consulta.lower()
    resultados_tabla = []
    if any(p in consulta_lower for p in ['formula', 'formulas', 'magistral', 'fm']):
        resultados_tabla.append("Claro! Estas son nuestras formulas magistrales:")
        resultados_tabla.append("-" * 40)
        for r in formulas:
            resultados_tabla.append(f"\n{r['CodFormula']}: {r['DescripcionFM']}\n   Unidad: {r['UnidadMedidaFM']}\n   Precio: S/ {r['CostoUnitarioFM']:.2f}\n   Estado: {r['EstadoFM']}")
    if any(p in consulta_lower for p in ['producto', 'productos', 'pt', 'terminado', 'medicamento']):
        resultados_tabla.append("Por supuesto! Estos son nuestros productos terminados:")
        resultados_tabla.append("-" * 40)
        for r in productos:
            resultados_tabla.append(f"\n{r['CodProducto']}: {r['DescripcionPT']}\n   Uso: {r['DescripcionUso']}\n   Unidad: {r['UnidadMedidaPT']}\n   Precio: S/ {r['CostoUnitarioPT']:.2f}\n   Stock: {r['StockPT']} unidades\n   Estado: {r['EstadoPT']}")
    if any(p in consulta_lower for p in ['medico', 'medicos', 'doctor', 'doctores', 'cmp']):
        resultados_tabla.append("Hola! Estos son los medicos con los que trabajamos:")
        resultados_tabla.append("-" * 40)
        for r in medicos:
            resultados_tabla.append(f"\nDr(a). {r['NombresM']} {r['ApellidosM']}\n   Colegiatura: {r['ColegiaturaMedico']}\n   Celular: {r['CelularM']}\n   Estado: {r['EstadoM']}")
    if any(p in consulta_lower for p in ['sede', 'sedes', 'local', 'locales', 'ubicacion', 'direccion']):
        resultados_tabla.append("Con gusto! Estas son nuestras sedes:")
        resultados_tabla.append("-" * 40)
        for r in sedes:
            resultados_tabla.append(f"\n{r['NombreSede']}\n   Direccion: {r['Direccion']}\n   Ciudad: {r['Ciudad']}\n   Region: {r['Region']}")
    if any(p in consulta_lower for p in ['cliente', 'clientes', 'paciente', 'pacientes']):
        resultados_tabla.append("Claro! Estos son nuestros clientes registrados:")
        resultados_tabla.append("-" * 40)
        for r in clientes:
            resultados_tabla.append(f"\n{r['NombresC']} {r['ApellidosC']}\n   DNI: {r['DniCliente']}\n   Celular: {r['CelularC']}")
    if any(p in consulta_lower for p in ['venta', 'ventas', 'factura', 'facturacion']):
        resultados_tabla.append("Aqui tienes! Estas son nuestras ventas realizadas:")
        resultados_tabla.append("-" * 40)
        resultados_tabla.append("\nFORMULAS MAGISTRALES:")
        for v in ventas_fm:
            formula = next((f for f in formulas if f['CodFormula'] == v['CodFormula']), None)
            cliente = next((c for c in clientes if c['ClienteKey'] == v['ClienteKey']), None)
            sede = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
            resultados_tabla.append(f"\n{v['CodVenta']}\n   Producto: {formula['DescripcionFM'] if formula else v['CodFormula']}\n   Cliente: {cliente['NombresC']+' '+cliente['ApellidosC'] if cliente else 'N/A'}\n   Sede: {sede['NombreSede'] if sede else 'N/A'}\n   Cantidad: {v['Cantidad']}\n   Total: S/ {v['SubTotalFM']:.2f}")
        resultados_tabla.append("\n\nPRODUCTOS TERMINADOS:")
        resultados_tabla.append("-" * 40)
        for v in ventas_pt:
            prod = next((p for p in productos if p['CodProducto'] == v['CodProducto']), None)
            cliente = next((c for c in clientes if c['ClienteKey'] == v['ClienteKey']), None)
            sede = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
            resultados_tabla.append(f"\n{v['CodVenta']}\n   Producto: {prod['DescripcionPT'] if prod else v['CodProducto']}\n   Cliente: {cliente['NombresC']+' '+cliente['ApellidosC'] if cliente else 'N/A'}\n   Sede: {sede['NombreSede'] if sede else 'N/A'}\n   Cantidad: {v['Cantidad']}\n   Total: S/ {v['SubTotalPT']:.2f}")
    if resultados_tabla:
        return "\n".join(resultados_tabla)
    return None

def generar_respuesta(consulta):
    respuesta_especifica = buscar_respuesta_especifica(consulta)
    if respuesta_especifica:
        return respuesta_especifica
    info_tabla = buscar_info_tabla(consulta)
    if info_tabla:
        return info_tabla
    intencion = detectar_intencion(consulta)
    if intencion == "no_respondable":
        return "Lo siento, no cuento con informacion sobre estadisticas de pacientes o ventas. Mi base de datos contiene informacion sobre productos, formulas magistrales, precios, disponibilidad, sedes y servicios. En que puedo ayudarte?"
    resultados = buscar(consulta, top_k=5)
    if not resultados or resultados[0]['similitud'] < 0.25:
        if intencion is None:
            return "No estoy seguro de entender tu pregunta. Puedo ayudarte con: precios de productos, disponibilidad, recomendaciones, informacion de sedes o servicios. Podrias ser mas especifico?"
    mejor = resultados[0] if resultados else None
    cat = mejor.get('categoria', '') if mejor else ''
    precio = mejor.get('precio', 0) if mejor else 0
    if intencion == "precio" and mejor:
        if cat == "Producto Terminado":
            resp = random.choice([
                f"El precio de {mejor['titulo']} es S/ {precio:.2f} por {mejor.get('unidad', 'unidad')}.",
                f"{mejor['titulo']} tiene un costo de S/ {precio:.2f}.",
                f"Por {mejor.get('unidad', 'unidad')} de {mejor['titulo']} son S/ {precio:.2f}.",
            ])
        elif cat == "Formula Magistral":
            resp = random.choice([
                f"La formula magistral {mejor['titulo']} tiene un costo de S/ {precio:.2f}.",
                f"{mejor['titulo']} cuesta S/ {precio:.2f} por {mejor.get('unidad', 'unidad')}.",
            ])
        else:
            resp = f"El precio es S/ {precio:.2f}."
    elif intencion == "disponibilidad" and mejor:
        stock = mejor.get('stock', 0)
        if cat == "Formula Magistral":
            resp = random.choice([
                f"Si, {mejor['titulo']} esta disponible. Se prepara con prescripcion medica.",
                f"Contamos con {mejor['titulo']}. Necesitas tu receta medica.",
            ])
        elif stock > 0:
            resp = random.choice([
                f"Si, tenemos {mejor['titulo']}. Hay {stock} unidades en stock.",
                f"{mejor['titulo']} esta disponible. Tenemos {stock} unidades.",
            ])
        else:
            resp = f"Lamentablemente {mejor['titulo']} se encuentra agotado."
    elif intencion == "recomendacion" and mejor:
        uso = mejor.get('uso', '')
        if cat == "Formula Magistral":
            resp = random.choice([
                f"Para tu caso, te recomiendo {mejor['titulo']}. {uso} Costo: S/ {precio:.2f}. Requiere prescripcion medica.",
                f"Podria ayudarte {mejor['titulo']}. {uso} Precio: S/ {precio:.2f}.",
            ])
        elif cat == "Producto Terminado":
            stock = mejor.get('stock', 0)
            resp = random.choice([
                f"Te recomiendo {mejor['titulo']}. {uso} Precio: S/ {precio:.2f}. Stock: {stock} unidades.",
                f"Podria servirte {mejor['titulo']}. {uso} S/ {precio:.2f}. Hay {stock} unidades disponibles.",
            ])
        else:
            resp = f"{mejor['descripcion']}"
    elif intencion == "informacion" and mejor:
        resp = f"{mejor['descripcion']}"
    elif intencion == "ubicacion" and mejor:
        if cat == "Sede":
            resp = random.choice([
                f"{mejor['titulo']}\n{mejor['descripcion']}",
                f"Claro! {mejor['descripcion']}",
            ])
        else:
            sedes_res = [r for r in resultados if r.get('categoria') == 'Sede']
            if sedes_res:
                resp = sedes_res[0]['descripcion']
            else:
                resp = "Contamos con sedes en Juliaca y Puno. Te gustaria conocer alguna en especifico?"
    elif intencion == "medico":
        medicos_res = [r for r in resultados if r.get('categoria') == 'Medico']
        if medicos_res:
            resp = medicos_res[0]['descripcion']
        else:
            resp = "Trabajamos con varios medicos asociados. Necesitas informacion sobre algun medico?"
    elif mejor:
        if cat == "Producto Terminado":
            uso = mejor.get('uso', '')
            stock = mejor.get('stock', 0)
            resp = f"{mejor['titulo']}\n{uso}\nPrecio: S/ {precio:.2f} | Stock: {stock} unidades."
        elif cat == "Formula Magistral":
            resp = f"{mejor['titulo']} - S/ {precio:.2f} ({mejor.get('unidad', 'unidad')})."
        else:
            resp = f"{mejor['descripcion']}"
    else:
        resp = "No encontre informacion relevante. Podrias reformular tu pregunta?"
    extras = [r for r in resultados[1:] if r['similitud'] > 0.3 and r.get('precio')]
    if extras:
        resp += "\n\nTambien tenemos: " + "; ".join(f"{r['titulo']} (S/ {r.get('precio', 0):.2f})" for r in extras[:2])
    return resp

# --- Modelo ML2: K-Means Segmentacion de Clientes ---
print("[ML] Cargando modelo de segmentacion K-Means...")
clientes_segmentados = None
clusters_info = None

def calcular_segmentacion_clientes():
    stats = []
    for c in clientes:
        ck = c['ClienteKey']
        compras_fm = sum(v['Cantidad'] for v in ventas_fm if v['ClienteKey'] == ck)
        gasto_fm = sum(v['SubTotalFM'] for v in ventas_fm if v['ClienteKey'] == ck)
        compras_pt = sum(v['Cantidad'] for v in ventas_pt if v['ClienteKey'] == ck)
        gasto_pt = sum(v['SubTotalPT'] for v in ventas_pt if v['ClienteKey'] == ck)
        stats.append({
            'ClienteKey': ck,
            'Nombre': f"{c['NombresC']} {c['ApellidosC']}",
            'DniCliente': c['DniCliente'],
            'TotalCompras': compras_fm + compras_pt,
            'GastoTotal': round(gasto_fm + gasto_pt, 2)
        })
    if len(stats) < 3:
        return [], []
    X = np.array([[s['TotalCompras'], s['GastoTotal']] for s in stats])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    for i, s in enumerate(stats):
        s['Cluster'] = int(clusters[i])
    clusters_info_list = []
    for k in range(3):
        miembros = [s for s in stats if s['Cluster'] == k]
        if miembros:
            gasto_prom = sum(s['GastoTotal'] for s in miembros) / len(miembros)
            compras_prom = sum(s['TotalCompras'] for s in miembros) / len(miembros)
            clusters_info_list.append({
                "cluster": k, "nombre": None,
                "cantidad": len(miembros),
                "gasto_promedio": round(gasto_prom, 2),
                "compras_promedio": round(compras_prom, 1),
                "accion": None
            })
    clusters_info_list.sort(key=lambda x: x['gasto_promedio'], reverse=True)
    nombres = ["VIP", "Ocasional", "Nuevo"]
    acciones = [
        "Programa de fidelizacion, descuentos por volumen",
        "Ofertas, facilidades de pago",
        "Campanas de bienvenida y retencion"
    ]
    for i, cl in enumerate(clusters_info_list):
        cl["nombre"] = nombres[i]
        cl["accion"] = acciones[i]
    return stats, clusters_info_list

# --- API Endpoints ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('usuario', '').strip()
    password = data.get('contrasena', '').strip()
    if not username or not password:
        return jsonify({"exito": False, "mensaje": "Usuario y contrasena son requeridos"})
    user = next((u for u in usuarios if u['Username'] == username and u['Activo']), None)
    if user and user['PasswordHash'] == password:
        return jsonify({"exito": True, "usuario": user['Username'], "nombre": f"{user['Nombres']} {user['Apellidos']}", "rol": user['Rol']})
    return jsonify({"exito": False, "mensaje": "Usuario o contrasena incorrectos"})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    consulta = data.get('mensaje', '').strip()
    if not consulta:
        return jsonify({"error": "Mensaje vacio"}), 400
    respuesta = generar_respuesta(consulta)
    return jsonify({"respuesta": respuesta})

@app.route('/api/salud', methods=['GET'])
def salud():
    return jsonify({"status": "ok", "documentos": len(documentos)})

@app.route('/api/recomendar', methods=['POST'])
def recomendar():
    return jsonify({"mensaje": "Endpoint de recomendacion no disponible. Use /api/chat."})

@app.route('/api/metricas', methods=['GET'])
def obtener_metricas():
    total_fm = sum(v['SubTotalFM'] for v in ventas_fm)
    total_pt = sum(v['SubTotalPT'] for v in ventas_pt)
    total_ventas = total_fm + total_pt
    juliaca_fm = sum(v['SubTotalFM'] for v in ventas_fm if next(s['Ciudad'] for s in sedes if s['SedeKey'] == v['SedeKey']) == 'Juliaca')
    juliaca_pt = sum(v['SubTotalPT'] for v in ventas_pt if next(s['Ciudad'] for s in sedes if s['SedeKey'] == v['SedeKey']) == 'Juliaca')
    puno_fm = total_fm - juliaca_fm
    puno_pt = total_pt - juliaca_pt
    ventas_por_mes_dict = {}
    for v in ventas_fm:
        t = next((t for t in tiempos_fm if t['FechaKey'] == v['FechaKey']), None)
        if t:
            mes = t['MesNombre']
            ventas_por_mes_dict[mes] = ventas_por_mes_dict.get(mes, 0) + v['SubTotalFM']
    for v in ventas_pt:
        t = next((t for t in tiempos_pt if t['FechaKey'] == v['FechaKey']), None)
        if t:
            mes = t['MesNombre']
            ventas_por_mes_dict[mes] = ventas_por_mes_dict.get(mes, 0) + v['SubTotalPT']
    orden_meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    ventas_por_mes = [{"mes": m, "total": round(ventas_por_mes_dict.get(m, 0), 2)} for m in orden_meses if m in ventas_por_mes_dict]
    ventas_fm_pt_mes = []
    for m in orden_meses:
        if m in ventas_por_mes_dict:
            fm_val = sum(v['SubTotalFM'] for v in ventas_fm if next((t['MesNombre'] for t in tiempos_fm if t['FechaKey'] == v['FechaKey']), None) == m)
            pt_val = sum(v['SubTotalPT'] for v in ventas_pt if next((t['MesNombre'] for t in tiempos_pt if t['FechaKey'] == v['FechaKey']), None) == m)
            ventas_fm_pt_mes.append({"mes": m, "fm": round(fm_val, 2), "pt": round(pt_val, 2)})
    ventas_sede_dict = {}
    for v in ventas_fm:
        s = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
        if s:
            nombre = s['NombreSede']
            if nombre not in ventas_sede_dict:
                ventas_sede_dict[nombre] = {"sede": nombre, "fm": 0, "pt": 0}
            ventas_sede_dict[nombre]["fm"] += v['SubTotalFM']
    for v in ventas_pt:
        s = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
        if s:
            nombre = s['NombreSede']
            if nombre not in ventas_sede_dict:
                ventas_sede_dict[nombre] = {"sede": nombre, "fm": 0, "pt": 0}
            ventas_sede_dict[nombre]["pt"] += v['SubTotalPT']
    ventas_sede_resumen = [{"sede": v["sede"], "fm": round(v["fm"], 2), "pt": round(v["pt"], 2)} for v in ventas_sede_dict.values()]
    return jsonify({
        "ingresos_totales": round(total_ventas, 2),
        "ingresos_fm": round(total_fm, 2),
        "ingresos_pt": round(total_pt, 2),
        "porcentaje_fm": round((total_fm / total_ventas * 100) if total_ventas > 0 else 0, 1),
        "porcentaje_pt": round((total_pt / total_ventas * 100) if total_ventas > 0 else 0, 1),
        "juliaca_total": round(juliaca_fm + juliaca_pt, 2),
        "puno_total": round(puno_fm + puno_pt, 2),
        "juliaca_fm": round(juliaca_fm, 2),
        "juliaca_pt": round(juliaca_pt, 2),
        "puno_fm": round(puno_fm, 2),
        "puno_pt": round(puno_pt, 2),
        "total_productos": len(productos),
        "total_formulas": len(formulas),
        "total_clientes": len(clientes),
        "total_medicos": len(medicos),
        "total_sedes": len(sedes),
        "stock_total": sum(p['StockPT'] for p in productos),
        "ventas_por_mes": ventas_por_mes,
        "ventas_fm_pt_mes": ventas_fm_pt_mes,
        "ventas_sede_resumen": ventas_sede_resumen
    })

@app.route('/api/clientes/segmentacion', methods=['GET'])
def segmentacion_clientes():
    global clientes_segmentados, clusters_info
    try:
        if clientes_segmentados is None:
            clientes_segmentados, clusters_info = calcular_segmentacion_clientes()
        return jsonify({
            "clientes": clientes_segmentados if clientes_segmentados else [],
            "clusters": clusters_info if clusters_info else [],
            "total": len(clientes_segmentados) if clientes_segmentados else 0
        })
    except Exception as e:
        print(f"[ERROR] segmentacion: {e}")
        return jsonify({"clientes": [], "clusters": [], "total": 0})

# --- CRUD Endpoints (usan JSON en memoria) ---

@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    return jsonify(productos)

@app.route('/api/productos', methods=['POST'])
def crear_producto():
    data = request.json
    productos.append(data)
    return jsonify({"mensaje": "Producto creado exitosamente"})

@app.route('/api/productos/<cod>', methods=['PUT'])
def actualizar_producto(cod):
    data = request.json
    for i, p in enumerate(productos):
        if p['CodProducto'] == cod:
            productos[i] = data
            return jsonify({"mensaje": "Producto actualizado"})
    return jsonify({"mensaje": "Producto no encontrado"}), 404

@app.route('/api/productos/<cod>', methods=['DELETE'])
def eliminar_producto(cod):
    global productos
    productos = [p for p in productos if p['CodProducto'] != cod]
    return jsonify({"mensaje": "Producto eliminado"})

@app.route('/api/formulas', methods=['GET'])
def obtener_formulas():
    return jsonify(formulas)

@app.route('/api/formulas', methods=['POST'])
def crear_formula():
    data = request.json
    formulas.append(data)
    return jsonify({"mensaje": "Formula creada exitosamente"})

@app.route('/api/formulas/<cod>', methods=['PUT'])
def actualizar_formula(cod):
    data = request.json
    for i, f in enumerate(formulas):
        if f['CodFormula'] == cod:
            formulas[i] = data
            return jsonify({"mensaje": "Formula actualizada"})
    return jsonify({"mensaje": "Formula no encontrada"}), 404

@app.route('/api/formulas/<cod>', methods=['DELETE'])
def eliminar_formula(cod):
    global formulas
    formulas = [f for f in formulas if f['CodFormula'] != cod]
    return jsonify({"mensaje": "Formula eliminada"})

@app.route('/api/clientes', methods=['GET'])
def obtener_clientes():
    return jsonify(clientes)

@app.route('/api/clientes', methods=['POST'])
def crear_cliente():
    data = request.json
    clientes.append(data)
    return jsonify({"mensaje": "Cliente creado exitosamente"})

@app.route('/api/clientes/<key>', methods=['PUT'])
def actualizar_cliente(key):
    data = request.json
    for i, c in enumerate(clientes):
        if str(c['ClienteKey']) == str(key):
            clientes[i] = data
            return jsonify({"mensaje": "Cliente actualizado"})
    return jsonify({"mensaje": "Cliente no encontrado"}), 404

@app.route('/api/clientes/<key>', methods=['DELETE'])
def eliminar_cliente(key):
    global clientes
    clientes = [c for c in clientes if str(c['ClienteKey']) != str(key)]
    return jsonify({"mensaje": "Cliente eliminado"})

@app.route('/api/medicos', methods=['GET'])
def obtener_medicos():
    return jsonify(medicos)

@app.route('/api/medicos', methods=['POST'])
def crear_medico():
    data = request.json
    medicos.append(data)
    return jsonify({"mensaje": "Medico creado exitosamente"})

@app.route('/api/medicos/<key>', methods=['PUT'])
def actualizar_medico(key):
    data = request.json
    for i, m in enumerate(medicos):
        if str(m['MedicoKey']) == str(key):
            medicos[i] = data
            return jsonify({"mensaje": "Medico actualizado"})
    return jsonify({"mensaje": "Medico no encontrado"}), 404

@app.route('/api/medicos/<key>', methods=['DELETE'])
def eliminar_medico(key):
    global medicos
    medicos = [m for m in medicos if str(m['MedicoKey']) != str(key)]
    return jsonify({"mensaje": "Medico eliminado"})

@app.route('/api/sedes', methods=['GET'])
def obtener_sedes():
    return jsonify(sedes)

@app.route('/api/sedes', methods=['POST'])
def crear_sede():
    data = request.json
    sedes.append(data)
    return jsonify({"mensaje": "Sede creada exitosamente"})

@app.route('/api/sedes/<key>', methods=['PUT'])
def actualizar_sede(key):
    data = request.json
    for i, s in enumerate(sedes):
        if str(s['SedeKey']) == str(key):
            sedes[i] = data
            return jsonify({"mensaje": "Sede actualizada"})
    return jsonify({"mensaje": "Sede no encontrada"}), 404

@app.route('/api/sedes/<key>', methods=['DELETE'])
def eliminar_sede(key):
    global sedes
    sedes = [s for s in sedes if str(s['SedeKey']) != str(key)]
    return jsonify({"mensaje": "Sede eliminada"})

@app.route('/api/ventas', methods=['GET'])
def obtener_ventas():
    resultado = []
    for v in ventas_fm:
        formula = next((f for f in formulas if f['CodFormula'] == v['CodFormula']), None)
        cliente = next((c for c in clientes if c['ClienteKey'] == v['ClienteKey']), None)
        sede = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
        resultado.append({
            "CodVenta": v['CodVenta'], "Codigo": v['CodFormula'],
            "Producto": formula['DescripcionFM'] if formula else v['CodFormula'],
            "Cliente": f"{cliente['NombresC']} {cliente['ApellidosC']}" if cliente else "N/A",
            "Sede": sede['NombreSede'] if sede else "N/A",
            "Cantidad": v['Cantidad'], "SubTotal": v['SubTotalFM'], "Tipo": "FM"
        })
    for v in ventas_pt:
        prod = next((p for p in productos if p['CodProducto'] == v['CodProducto']), None)
        cliente = next((c for c in clientes if c['ClienteKey'] == v['ClienteKey']), None)
        sede = next((s for s in sedes if s['SedeKey'] == v['SedeKey']), None)
        resultado.append({
            "CodVenta": v['CodVenta'], "Codigo": v['CodProducto'],
            "Producto": prod['DescripcionPT'] if prod else v['CodProducto'],
            "Cliente": f"{cliente['NombresC']} {cliente['ApellidosC']}" if cliente else "N/A",
            "Sede": sede['NombreSede'] if sede else "N/A",
            "Cantidad": v['Cantidad'], "SubTotal": v['SubTotalPT'], "Tipo": "PT"
        })
    return jsonify(resultado)

@app.route('/api/ventas/dropdowns', methods=['GET'])
def ventas_dropdowns():
    return jsonify({
        "formulas": [{"CodFormula": f['CodFormula'], "DescripcionFM": f['DescripcionFM'], "CostoUnitarioFM": f['CostoUnitarioFM']} for f in formulas if f['EstadoFM'] == 'Activo'],
        "productos": [{"CodProducto": p['CodProducto'], "DescripcionPT": p['DescripcionPT'], "CostoUnitarioPT": p['CostoUnitarioPT']} for p in productos if p['EstadoPT'] == 'Activo'],
        "clientes": [{"ClienteKey": c['ClienteKey'], "Nombre": f"{c['NombresC']} {c['ApellidosC']}"} for c in clientes],
        "sedes": [{"SedeKey": s['SedeKey'], "NombreSede": s['NombreSede']} for s in sedes],
        "medicos": [{"MedicoKey": m['MedicoKey'], "Nombre": f"{m['NombresM']} {m['ApellidosM']}"} for m in medicos if m['EstadoM'] == 'Activo'],
        "fechas_fm": [{"FechaKey": t['FechaKey'], "Fecha": t['Fecha']} for t in tiempos_fm],
        "fechas_pt": [{"FechaKey": t['FechaKey'], "Fecha": t['Fecha']} for t in tiempos_pt]
    })

@app.route('/api/ventas', methods=['POST'])
def crear_venta():
    data = request.json
    try:
        if data.get('tipo', 'FM') == 'FM':
            ventas_fm.append({
                "CodVenta": data['codVenta'], "CodFormula": data['codProducto'],
                "FechaKey": int(data['fechaKey']), "ClienteKey": int(data['clienteKey']),
                "SedeKey": int(data['sedeKey']), "MedicoKey": int(data['medicoKey']),
                "Medidas": data.get('medidas', ''), "Cantidad": int(data['cantidad']),
                "CostoUnitarioFM": float(data['costoUnitario']), "SubTotalFM": float(data['subtotal'])
            })
        else:
            ventas_pt.append({
                "CodVenta": data['codVenta'], "CodProducto": data['codProducto'],
                "FechaKey": int(data['fechaKey']), "ClienteKey": int(data['clienteKey']),
                "SedeKey": int(data['sedeKey']), "Medidas": data.get('medidas', ''),
                "Cantidad": int(data['cantidad']), "CostoUnitarioPT": float(data['costoUnitario']),
                "SubTotalPT": float(data['subtotal']), "StockDespues": int(data.get('stockDespues', 0))
            })
        return jsonify({"exito": True, "mensaje": "Venta creada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})

@app.route('/api/ventas/<cod>/<tipo>', methods=['PUT'])
def editar_venta(cod, tipo):
    data = request.json
    try:
        if tipo == 'FM':
            for i, v in enumerate(ventas_fm):
                if v['CodVenta'] == cod:
                    ventas_fm[i].update({
                        "CodFormula": data['codProducto'],
                        "FechaKey": int(data['fechaKey']), "ClienteKey": int(data['clienteKey']),
                        "SedeKey": int(data['sedeKey']), "MedicoKey": int(data['medicoKey']),
                        "Medidas": data.get('medidas', ''), "Cantidad": int(data['cantidad']),
                        "CostoUnitarioFM": float(data['costoUnitario']), "SubTotalFM": float(data['subtotal'])
                    })
                    break
        else:
            for i, v in enumerate(ventas_pt):
                if v['CodVenta'] == cod:
                    ventas_pt[i].update({
                        "CodProducto": data['codProducto'],
                        "FechaKey": int(data['fechaKey']), "ClienteKey": int(data['clienteKey']),
                        "SedeKey": int(data['sedeKey']), "Medidas": data.get('medidas', ''),
                        "Cantidad": int(data['cantidad']), "CostoUnitarioPT": float(data['costoUnitario']),
                        "SubTotalPT": float(data['subtotal']), "StockDespues": int(data.get('stockDespues', 0))
                    })
                    break
        return jsonify({"exito": True, "mensaje": "Venta actualizada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})

@app.route('/api/ventas/<cod>/<tipo>', methods=['DELETE'])
def eliminar_venta(cod, tipo):
    try:
        if tipo == 'FM':
            global ventas_fm
            ventas_fm = [v for v in ventas_fm if v['CodVenta'] != cod]
        else:
            global ventas_pt
            ventas_pt = [v for v in ventas_pt if v['CodVenta'] != cod]
        return jsonify({"exito": True, "mensaje": "Venta eliminada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})

if __name__ == '__main__':
    print("[API] Servidor iniciado en http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
