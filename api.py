"""
QbD Farmacia Magistral - Backend API
Flask + ML + SQL Server
El chatbot de la web consume esta API.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
import random
import pyodbc
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

load_dotenv()

app = Flask(__name__)
CORS(app)

# Sinónimos médicos
SINONIMOS = {
    "piel": "piel dermatitis crema tópica cutánea",
    "hongos": "antimicosis antifúngico clotrimazol micosis fungal",
    "tos": "antitusivo dextrometorfano jarabe respiratorio",
    "dolor": "analgésico antiinflamatorio ibuprofeno paracetamol",
    "fiebre": "antipirético paracetamol temperatura",
    "estómago": "gastritis úlcera reflujo omeprazol gástrico digestión",
    "infección": "antibiótico amoxicilina bacteriana bacteriano",
    "alergia": "antihistamínico loratadina rinitis estornudo",
    "antibiótico": "amoxicilina infección antibacteriano",
    "crema": "tópico pomada ungüento dermatológico",
    "médico": "doctor colegiatura receta prescripción",
    "sede": "ubicación dirección local sucursal",
    "dolor de cabeza": "paracetamol analgésico migraña cefalea",
    "dolor de muelas": "paracetamol ibuprofeno analgésico dental",
    "dolor de espalda": "ibuprofeno antiinflamatorio muscular",
    "gastritis": "omeprazol acidez estómago reflujo úlcera",
    "reflujo": "omeprazol gastroesofágico acidez gástrica",
    "infección urinaria": "amoxicilina antibiótico bacteriano",
    "amigdalitis": "amoxicilina antibiótico infección garganta",
    "neumonía": "amoxicilina antibiótico pulmón infección respiratoria",
    "rinitis": "loratadina antihistamínico alergia estornudo picazón",
    "urticaria": "loratadina antihistamínico alergia picazón piel",
    "artritis": "ibuprofeno antiinflamatorio inflamación articulaciones",
    "dolor muscular": "ibuprofeno antiinflamatorio inflamación",
    "cólico": "ibuprofeno antiinflamatorio dolor abdominal",
    "alopecia": "minoxidil crecimiento capilar cabello",
    "caída del cabello": "minoxidil alopecia crecimiento capilar",
    "qué medicamento": "producto medicamento fórmula",
    "qué producto": "producto medicamento fórmula",
    "cuánto cuesta": "precio costo valor",
    "cuánto vale": "precio costo valor",
    "cuánto sale": "precio costo valor",
    "hay stock": "disponible stock unidades",
    "tienen": "disponible stock unidades",
    "dirección": "ubicación dirección sede",
    "dónde": "ubicación dirección sede",
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

# --- Conexión BD ---
def get_db():
    cadena = (
        f"DRIVER={{{os.getenv('DB_DRIVER')}}};"
        f"SERVER={os.getenv('DB_SERVIDOR')};"
        f"DATABASE={os.getenv('DB_BASE')};"
        f"UID={os.getenv('DB_USUARIO')};"
        f"PWD={os.getenv('DB_CONTRASENA')};"
    )
    return pyodbc.connect(cadena)

def consultar(conn, sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    columnas = [desc[0] for desc in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

# --- Cargar conocimiento ---
def cargar_conocimiento():
    conn = get_db()
    documentos = []

    for r in consultar(conn, "SELECT * FROM DIM_FormulaMagistral"):
        desc = r['DescripcionFM']
        texto = f"Fórmula magistral {r['CodFormula']}: {desc}. Unidad: {r['UnidadMedidaFM']}. Costo: S/ {r['CostoUnitarioFM']}."
        if "piel" in desc.lower() or "dermatol" in desc.lower():
            texto += " Tratamiento para piel, dermatitis, hidratación cutánea."
        if "amoxicilina" in desc.lower():
            texto += " Antibiótico para infecciones bacterianas."
        if "tos" in desc.lower():
            texto += " Jarabe antitusivo para aliviar la tos."
        if "clotrimazol" in desc.lower():
            texto += " Crema antifúngica para hongos en piel, micosis."
        if "minoxidil" in desc.lower():
            texto += " Tratamiento para alopecia, crecimiento capilar."
        documentos.append({"id": r['CodFormula'], "categoria": "Fórmula Magistral", "titulo": desc, "descripcion": texto, "precio": float(r['CostoUnitarioFM']), "unidad": r['UnidadMedidaFM'], "estado": r['EstadoFM']})

    for r in consultar(conn, "SELECT * FROM DIM_ProductoTerminado"):
        desc = r['DescripcionPT']
        uso = r['DescripcionUso']
        texto = f"Producto {r['CodProducto']}: {desc}. Uso: {uso}. Precio: S/ {r['CostoUnitarioPT']}. Stock: {r['StockPT']}."
        documentos.append({"id": r['CodProducto'], "categoria": "Producto Terminado", "titulo": desc, "descripcion": texto, "uso": uso, "precio": float(r['CostoUnitarioPT']), "unidad": r['UnidadMedidaPT'], "stock": r['StockPT'], "estado": r['EstadoPT']})

    for r in consultar(conn, "SELECT s.*, (SELECT COUNT(*) FROM FACT_VentaFM WHERE SedeKey=s.SedeKey)+(SELECT COUNT(*) FROM FACT_VentaPT WHERE SedeKey=s.SedeKey) AS TotalVentas FROM DIM_Sede s"):
        documentos.append({"id": f"SEDE-{r['SedeKey']}", "categoria": "Sede", "titulo": r['NombreSede'], "descripcion": f"Sede {r['NombreSede']}. Ubicación: {r['Direccion']}, {r['Ciudad']}, {r['Region']}."})

    for r in consultar(conn, "SELECT m.*, (SELECT COUNT(*) FROM FACT_VentaFM WHERE MedicoKey=m.MedicoKey) AS Recetas FROM DIM_Medico m"):
        documentos.append({"id": f"MED-{r['MedicoKey']}", "categoria": "Médico", "titulo": f"Dr(a). {r['NombresM']} {r['ApellidosM']}", "descripcion": f"Médico {r['NombresM']} {r['ApellidosM']}, colegiatura {r['ColegiaturaMedico']}. Estado: {r['EstadoM']}."})

    general = [
        {"id": "GEN-001", "categoria": "General", "titulo": "QbD Farmacia", "descripcion": "QbD Farmacia Magistral S.A.C. es una empresa farmacéutica peruana dedicada a fórmulas magistrales y productos farmacéuticos. Inició en septiembre 2021 en Juliaca y Puno."},
        {"id": "GEN-002", "categoria": "General", "titulo": "Misión", "descripcion": "Brindar soluciones farmacéuticas personalizadas con calidad, responsabilidad y compromiso."},
        {"id": "GEN-003", "categoria": "General", "titulo": "Fórmula magistral", "descripcion": "Fórmula magistral es un medicamento elaborado para un paciente según prescripción médica."},
        {"id": "GEN-004", "categoria": "General", "titulo": "Servicios", "descripcion": "Servicios: fórmulas magistrales, productos farmacéuticos, atención personalizada, orientación y seguimiento."},
        {"id": "GEN-005", "categoria": "General", "titulo": "Horarios", "descripcion": "Atención de lunes a sábado en sedes de Juliaca y Puno."},
    ]
    documentos.extend(general)

    conn.close()
    return documentos

# --- Modelo ML ---
print("[ML] Cargando modelo chatbot...")
modelo_ml = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
documentos = cargar_conocimiento()
textos = [f"{d['titulo']}. {d['descripcion']}" for d in documentos]
embeddings = modelo_ml.encode(textos, convert_to_tensor=True)
print(f"[ML] Modelo chatbot listo. {len(documentos)} documentos indexados.")

# --- Modelo ML 2: Segmentacion de Clientes (K-Means) ---
print("[ML] Cargando modelo de segmentacion K-Means...")
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

def obtener_datos_clientes():
    """Obtiene datos de clientes para el modelo K-Means desde la BD."""
    conn = get_db()
    
    sql = """
    SELECT 
        c.ClienteKey,
        c.NombresC + ' ' + c.ApellidosC AS Nombre,
        c.DniCliente,
        ISNULL(fm.TotalComprasFM, 0) AS ComprasFM,
        ISNULL(fm.GastoFM, 0) AS GastoFM,
        ISNULL(pt.TotalComprasPT, 0) AS ComprasPT,
        ISNULL(pt.GastoPT, 0) AS GastoPT,
        ISNULL(fm.TotalComprasFM, 0) + ISNULL(pt.TotalComprasPT, 0) AS TotalCompras,
        ISNULL(fm.GastoFM, 0) + ISNULL(pt.GastoPT, 0) AS GastoTotal
    FROM DIM_Cliente c
    LEFT JOIN (
        SELECT ClienteKey, COUNT(*) AS TotalComprasFM, SUM(SubTotalFM) AS GastoFM
        FROM FACT_VentaFM GROUP BY ClienteKey
    ) fm ON c.ClienteKey = fm.ClienteKey
    LEFT JOIN (
        SELECT ClienteKey, COUNT(*) AS TotalComprasPT, SUM(SubTotalPT) AS GastoPT
        FROM FACT_VentaPT GROUP BY ClienteKey
    ) pt ON c.ClienteKey = pt.ClienteKey
    """
    
    clientes = consultar(conn, sql)
    conn.close()
    return clientes

def entrenar_kmeans():
    """Entrena el modelo K-Means con los datos de clientes."""
    clientes = obtener_datos_clientes()
    
    if len(clientes) < 3:
        return None, None, None
    
    X = np.array([[c['TotalCompras'], c['GastoTotal']] for c in clientes])
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    for i, c in enumerate(clientes):
        c['Cluster'] = int(clusters[i])
    
    centroides = scaler.inverse_transform(kmeans.cluster_centers_)
    
    clusters_info = []
    for k in range(3):
        miembros = [c for c in clientes if c['Cluster'] == k]
        if miembros:
            gasto_prom = sum(c['GastoTotal'] for c in miembros) / len(miembros)
            compras_prom = sum(c['TotalCompras'] for c in miembros) / len(miembros)
            clusters_info.append({
                "cluster": k,
                "nombre": None,  # se asigna después por ranking
                "cantidad": len(miembros),
                "gasto_promedio": round(gasto_prom, 2),
                "compras_promedio": round(compras_prom, 1),
                "accion": None
            })
    
    # Ordenar por gasto promedio para asignar nombres únicos por ranking relativo
    clusters_info.sort(key=lambda x: x['gasto_promedio'], reverse=True)
    
    nombres = ["VIP", "Ocasional", "Nuevo"]
    acciones = [
        "Programa de fidelización, descuentos por volumen",
        "Ofertas, facilidades de pago",
        "Campañas de bienvenida y retención"
    ]
    for i, cl in enumerate(clusters_info):
        cl["nombre"] = nombres[i]
        cl["accion"] = acciones[i]
    
    return clientes, clusters_info, kmeans

clientes_segmentados = None
clusters_info = None
kmeans_model = None

def recomendar_por_sintomas(consulta):
    """Compatibilidad: retorna None (ya no se usa para recomendacion)."""
    return None

def buscar(consulta, top_k=3):
    expandida = expandir_consulta(consulta)
    emb = modelo_ml.encode(expandida, convert_to_tensor=True)
    sims = util.cos_sim(emb, embeddings)[0]
    top_idx = sims.argsort(descending=True)[:top_k]
    return [{**documentos[i.item()], "similitud": round(sims[i.item()].item(), 4)} for i in top_idx]

import random

def buscar_respuesta_especifica(consulta):
    """Busca respuestas específicas como dirección de una sede, precio de un producto, etc."""
    conn = get_db()
    consulta_lower = consulta.lower()
    respuesta = None

    # Buscar sede específica por nombre
    sedes = consultar(conn, "SELECT * FROM DIM_Sede")
    for s in sedes:
        nombre_lower = s['NombreSede'].lower()
        # Si la consulta menciona el nombre de la sede
        if any(palabra in consulta_lower for palabra in nombre_lower.split() if len(palabra) > 3):
            if any(p in consulta_lower for p in ['dirección', 'direccion', 'ubicación', 'ubicacion', 'dónde', 'donde', 'queda']):
                respuesta = f"📍 {s['NombreSede']}\nDirección: {s['Direccion']}\nCiudad: {s['Ciudad']}, {s['Region']}"
                break

    # Buscar producto específico por nombre
    if not respuesta:
        productos = consultar(conn, "SELECT * FROM DIM_ProductoTerminado")
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
                elif any(px in consulta_lower for px in ['uso', 'sirve', 'para qué', 'para que', 'qué hace', 'que hace', 'beneficio']):
                    respuesta = f"🔹 {p['DescripcionPT']}\nUso: {p['DescripcionUso']}\nPrecio: S/ {p['CostoUnitarioPT']:.2f}"
                    break

    # Buscar fórmula magistral específica
    if not respuesta:
        formulas = consultar(conn, "SELECT * FROM DIM_FormulaMagistral")
        for f in formulas:
            nombre_lower = f['DescripcionFM'].lower()
            palabras = [w for w in nombre_lower.split() if len(w) > 3]
            if any(palabra in consulta_lower for palabra in palabras):
                if any(px in consulta_lower for px in ['precio', 'cuesta', 'vale', 'sale', 'costo']):
                    respuesta = f"La fórmula magistral {f['DescripcionFM']} cuesta S/ {f['CostoUnitarioFM']:.2f} por {f['UnidadMedidaFM']}."
                    break

    conn.close()
    return respuesta

def buscar_info_tabla(consulta):
    """Cuando mencionan una tabla, busca toda su información."""
    conn = get_db()
    consulta_lower = consulta.lower()
    resultados_tabla = []

    # FÓRMULAS MAGISTRALES
    if any(p in consulta_lower for p in ['fórmula', 'formula', 'magistral', 'fm', 'fórmulas', 'formulas']):
        sql = "SELECT * FROM DIM_FormulaMagistral"
        resultados_tabla.append("¡Claro! Estas son nuestras fórmulas magistrales:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql):
            resultados_tabla.append(
                f"\n🔹 {r['CodFormula']}: {r['DescripcionFM']}\n"
                f"   Unidad: {r['UnidadMedidaFM']}\n"
                f"   Precio: S/ {r['CostoUnitarioFM']:.2f}\n"
                f"   Estado: {r['EstadoFM']}"
            )

    # PRODUCTOS TERMINADOS
    if any(p in consulta_lower for p in ['producto', 'productos', 'pt', 'terminado', 'terminados', 'medicamento', 'medicamentos']):
        sql = "SELECT * FROM DIM_ProductoTerminado"
        resultados_tabla.append("¡Por supuesto! Estos son nuestros productos terminados:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql):
            resultados_tabla.append(
                f"\n🔹 {r['CodProducto']}: {r['DescripcionPT']}\n"
                f"   Uso: {r['DescripcionUso']}\n"
                f"   Unidad: {r['UnidadMedidaPT']}\n"
                f"   Precio: S/ {r['CostoUnitarioPT']:.2f}\n"
                f"   Stock: {r['StockPT']} unidades\n"
                f"   Estado: {r['EstadoPT']}"
            )

    # MÉDICOS
    if any(p in consulta_lower for p in ['médico', 'medico', 'médicos', 'medicos', 'doctor', 'doctores', 'cmp']):
        sql = "SELECT * FROM DIM_Medico"
        resultados_tabla.append("¡Hola! Estos son los médicos con los que trabajamos:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql):
            resultados_tabla.append(
                f"\n🔹 Dr(a). {r['NombresM']} {r['ApellidosM']}\n"
                f"   Colegiatura: {r['ColegiaturaMedico']}\n"
                f"   Celular: {r['CelularM']}\n"
                f"   Estado: {r['EstadoM']}"
            )

    # SEDES
    if any(p in consulta_lower for p in ['sede', 'sedes', 'local', 'locales', 'ubicación', 'ubicacion', 'dirección', 'direccion']):
        sql = "SELECT * FROM DIM_Sede"
        resultados_tabla.append("¡Con gusto! Estas son nuestras sedes:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql):
            resultados_tabla.append(
                f"\n🔹 {r['NombreSede']}\n"
                f"   Dirección: {r['Direccion']}\n"
                f"   Ciudad: {r['Ciudad']}\n"
                f"   Región: {r['Region']}"
            )

    # CLIENTES
    if any(p in consulta_lower for p in ['cliente', 'clientes', 'paciente', 'pacientes']):
        sql = "SELECT * FROM DIM_Cliente"
        resultados_tabla.append("¡Claro! Estos son nuestros clientes registrados:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql):
            resultados_tabla.append(
                f"\n🔹 {r['NombresC']} {r['ApellidosC']}\n"
                f"   DNI: {r['DniCliente']}\n"
                f"   Celular: {r['CelularC']}"
            )

    # VENTAS
    if any(p in consulta_lower for p in ['venta', 'ventas', 'factura', 'facturación', 'facturacion']):
        sql_fm = """
            SELECT v.CodVenta, f.DescripcionFM, c.NombresC + ' ' + c.ApellidosC AS Cliente,
                   s.NombreSede, v.Cantidad, v.SubTotalFM
            FROM FACT_VentaFM v
            INNER JOIN DIM_FormulaMagistral f ON v.CodFormula = f.CodFormula
            INNER JOIN DIM_Cliente c ON v.ClienteKey = c.ClienteKey
            INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey
        """
        sql_pt = """
            SELECT v.CodVenta, p.DescripcionPT, c.NombresC + ' ' + c.ApellidosC AS Cliente,
                   s.NombreSede, v.Cantidad, v.SubTotalPT
            FROM FACT_VentaPT v
            INNER JOIN DIM_ProductoTerminado p ON v.CodProducto = p.CodProducto
            INNER JOIN DIM_Cliente c ON v.ClienteKey = c.ClienteKey
            INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey
        """
        resultados_tabla.append("¡Aquí tienes! Estas son nuestras ventas realizadas:")
        resultados_tabla.append("─" * 40)
        resultados_tabla.append("\n📊 FÓRMULAS MAGISTRALES:")
        for r in consultar(conn, sql_fm):
            resultados_tabla.append(
                f"\n🔹 {r['CodVenta']}\n"
                f"   Producto: {r['DescripcionFM']}\n"
                f"   Cliente: {r['Cliente']}\n"
                f"   Sede: {r['NombreSede']}\n"
                f"   Cantidad: {r['Cantidad']}\n"
                f"   Total: S/ {r['SubTotalFM']:.2f}"
            )
        resultados_tabla.append("\n\n📊 PRODUCTOS TERMINADOS:")
        resultados_tabla.append("─" * 40)
        for r in consultar(conn, sql_pt):
            resultados_tabla.append(
                f"\n🔹 {r['CodVenta']}\n"
                f"   Producto: {r['DescripcionPT']}\n"
                f"   Cliente: {r['Cliente']}\n"
                f"   Sede: {r['NombreSede']}\n"
                f"   Cantidad: {r['Cantidad']}\n"
                f"   Total: S/ {r['SubTotalPT']:.2f}"
            )

    conn.close()

    if resultados_tabla:
        return "\n".join(resultados_tabla)
    return None

def detectar_intencion(consulta):
    """Analiza la intención de la pregunta usando el modelo ML."""
    consulta_lower = consulta.lower()

    # PASO 1: Verificar si es una pregunta que NO podemos responder
    emb_consulta = modelo_ml.encode(consulta, convert_to_tensor=True)

    preguntas_no_respondables = [
        "cuántos pacientes han sido atendidos",
        "cuantos pacientes han sido atendidos",
        "cuántos pacientes atendidos",
        "cuántos clientes tenemos",
        "cuántas ventas hemos hecho",
        "cuánto hemos vendido",
        "cuál es la facturación",
        "cuáles son las estadísticas",
        "cuántos médicos tenemos",
        "cuántos doctores hay",
        "cuántas personas han venido",
        "cuántos atendisteis",
        "cuántos han venido",
        "cuántos se han atendido",
        "cuántos se atendieron",
        "cuántos pacientes hay",
        "cuántos clientes hay",
    ]

    for pregunta in preguntas_no_respondables:
        emb_no = modelo_ml.encode(pregunta, convert_to_tensor=True)
        sim = util.cos_sim(emb_consulta, emb_no)[0].item()
        if sim > 0.5:
            return "no_respondable"

    # PASO 2: Detectar intención positiva
    textos_intencion = {
        "precio": "¿Cuánto cuesta el producto? Precio, costo, valor, cuánto vale, cuánto sale, cuánto cuesta",
        "disponibilidad": "¿Hay disponible el producto? Stock, unidades, quedan, hay en existencia, hay disponible",
        "recomendacion": "Necesito un producto para mi dolencia. Me duele, tengo dolor, qué puedo tomar, qué me recomienda, necesito algo para",
        "informacion": "Cuéntame sobre el producto o servicio. Qué es, qué ofrecen, información, detalles, cuéntame",
        "ubicacion": "¿Dónde están ubicados? Sede, dirección, ubicación, dónde queda, dónde están",
        "medico": "¿Qué médicos recetan fórmulas magistrales? Médico que receta, doctor que prescribe",
    }

    mejor_intencion = None
    mejor_similitud = 0

    for intencion, texto in textos_intencion.items():
        emb_intencion = modelo_ml.encode(texto, convert_to_tensor=True)
        sim = util.cos_sim(emb_consulta, emb_intencion)[0].item()
        if sim > mejor_similitud:
            mejor_similitud = sim
            mejor_intencion = intencion

    if mejor_similitud > 0.4:
        return mejor_intencion

    return None

def generar_respuesta(consulta):
    # PASO 0: Buscar respuesta específica (dirección de sede, precio de producto, etc.)
    respuesta_especifica = buscar_respuesta_especifica(consulta)
    if respuesta_especifica:
        return respuesta_especifica

    # PASO 0.5: Si mencionan una tabla, buscar toda su información
    info_tabla = buscar_info_tabla(consulta)
    if info_tabla:
        return info_tabla

    # PASO 1: Detectar intención
    intencion = detectar_intencion(consulta)

    # Si es no respondable
    if intencion == "no_respondable":
        return (
            "Lo siento, no cuento con información sobre estadísticas de pacientes "
            "o ventas. Mi base de datos contiene información sobre productos, "
            "fórmulas magistrales, precios, disponibilidad, sedes y servicios. "
            "¿En qué puedo ayudarte?"
        )

    # PASO 2: Buscar en BD
    resultados = buscar(consulta, top_k=5)

    # Verificar relevancia
    if not resultados or resultados[0]['similitud'] < 0.25:
        if intencion is None:
            return (
                "No estoy seguro de entender tu pregunta. "
                "Puedo ayudarte con: precios de productos, disponibilidad, "
                "recomendaciones, información de sedes o servicios. "
                "¿Podrías ser más específico?"
            )

    mejor = resultados[0] if resultados else None
    cat = mejor.get('categoria', '') if mejor else ''
    precio = mejor.get('precio', 0) if mejor else 0

    # PASO 3: Buscar respuesta específica por intención + categoría

    # --- PRECIO ---
    if intencion == "precio" and mejor:
        if cat == "Producto Terminado":
            resp = random.choice([
                f"El precio de {mejor['titulo']} es S/ {precio:.2f} por {mejor.get('unidad', 'unidad')}.",
                f"{mejor['titulo']} tiene un costo de S/ {precio:.2f}.",
                f"Por {mejor.get('unidad', 'unidad')} de {mejor['titulo']} son S/ {precio:.2f}.",
            ])
        elif cat == "Fórmula Magistral":
            resp = random.choice([
                f"La fórmula magistral {mejor['titulo']} tiene un costo de S/ {precio:.2f}.",
                f"{mejor['titulo']} cuesta S/ {precio:.2f} por {mejor.get('unidad', 'unidad')}.",
            ])
        else:
            resp = f"El precio es S/ {precio:.2f}."

    # --- DISPONIBILIDAD / STOCK ---
    elif intencion == "disponibilidad" and mejor:
        stock = mejor.get('stock', 0)
        if cat == "Fórmula Magistral":
            resp = random.choice([
                f"Sí, {mejor['titulo']} está disponible. Se prepara con prescripción médica.",
                f"Contamos con {mejor['titulo']}. Necesitas tu receta médica.",
            ])
        elif stock > 0:
            resp = random.choice([
                f"Sí, tenemos {mejor['titulo']}. Hay {stock} unidades en stock.",
                f"{mejor['titulo']} está disponible. Tenemos {stock} unidades.",
            ])
        else:
            resp = f"Lamentablemente {mejor['titulo']} se encuentra agotado."

    # --- RECOMENDACIÓN (molestia / síntoma) ---
    elif intencion == "recomendacion" and mejor:
        uso = mejor.get('uso', '')
        if cat == "Fórmula Magistral":
            resp = random.choice([
                f"Para tu caso, te recomiendo {mejor['titulo']}. {uso} Costo: S/ {precio:.2f}. Requiere prescripción médica.",
                f"Podría ayudarte {mejor['titulo']}. {uso} Precio: S/ {precio:.2f}.",
            ])
        elif cat == "Producto Terminado":
            stock = mejor.get('stock', 0)
            resp = random.choice([
                f"Te recomiendo {mejor['titulo']}. {uso} Precio: S/ {precio:.2f}. Stock: {stock} unidades.",
                f"Podría servirte {mejor['titulo']}. {uso} S/ {precio:.2f}. Hay {stock} unidades disponibles.",
            ])
        else:
            resp = f"{mejor['descripcion']}"

    # --- INFORMACIÓN ---
    elif intencion == "informacion" and mejor:
        resp = f"{mejor['descripcion']}"

    # --- UBICACIÓN / SEDE ---
    elif intencion == "ubicacion" and mejor:
        if cat == "Sede":
            resp = random.choice([
                f"📍 {mejor['titulo']}\n{mejor['descripcion']}",
                f"¡Claro! {mejor['descripcion']}",
            ])
        else:
            sedes = [r for r in resultados if r.get('categoria') == 'Sede']
            if sedes:
                resp = sedes[0]['descripcion']
            else:
                resp = "Contamos con sedes en Juliaca y Puno. ¿Te gustaría conocer alguna en específico?"

    # --- MÉDICO ---
    elif intencion == "medico":
        medicos = [r for r in resultados if r.get('categoria') == 'Médico']
        if medicos:
            resp = medicos[0]['descripcion']
        else:
            resp = "Trabajamos con varios médicos asociados. ¿Necesitas información sobre algún médico?"

    # --- RESPUESTA POR DEFECTO ---
    elif mejor:
        if cat == "Producto Terminado":
            uso = mejor.get('uso', '')
            stock = mejor.get('stock', 0)
            resp = f"{mejor['titulo']}\n{uso}\nPrecio: S/ {precio:.2f} | Stock: {stock} unidades."
        elif cat == "Fórmula Magistral":
            resp = f"{mejor['titulo']} - S/ {precio:.2f} ({mejor.get('unidad', 'unidad')})."
        else:
            resp = f"{mejor['descripcion']}"

    else:
        resp = "No encontré información relevante. ¿Podrías reformular tu pregunta?"

    # Productos relacionados
    extras = [r for r in resultados[1:] if r['similitud'] > 0.3 and r.get('precio')]
    if extras:
        resp += "\n\nTambién tenemos: " + "; ".join(f"{r['titulo']} (S/ {r.get('precio', 0):.2f})" for r in extras[:2])

    return resp

# --- API ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('usuario', '').strip()
    password = data.get('contrasena', '').strip()
    
    if not username or not password:
        return jsonify({"exito": False, "mensaje": "Usuario y contraseña son requeridos"})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT Username, Nombres, Apellidos, Rol, PasswordHash FROM DIM_Usuario WHERE Username = ? AND Activo = 1",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row and row[4] == password:
        nombre = f"{row[1]} {row[2]}"
        return jsonify({
            "exito": True,
            "usuario": row[0],
            "nombre": nombre,
            "rol": row[3]
        })
    else:
        return jsonify({"exito": False, "mensaje": "Usuario o contraseña incorrectos"})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    consulta = data.get('mensaje', '').strip()
    if not consulta:
        return jsonify({"error": "Mensaje vacío"}), 400
    respuesta = generar_respuesta(consulta)
    return jsonify({"respuesta": respuesta})

@app.route('/api/salud', methods=['GET'])
def salud():
    return jsonify({"status": "ok", "documentos": len(documentos), "categorias_sintomas": len(SINTOMAS_PRODUCTOS)})

@app.route('/api/recomendar', methods=['POST'])
def recomendar():
    data = request.json
    consulta = data.get('mensaje', '').strip()
    if not consulta:
        return jsonify({"error": "Mensaje vacío"}), 400
    resultado = recomendar_por_sintomas(consulta)
    return jsonify(resultado)

# ====== CRUD ENDPOINTS ======

# PRODUCTOS TERMINADOS
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    conn = get_db()
    productos = consultar(conn, "SELECT * FROM DIM_ProductoTerminado")
    conn.close()
    return jsonify(productos)

@app.route('/api/productos', methods=['POST'])
def crear_producto():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO DIM_ProductoTerminado (CodProducto, DescripcionPT, DescripcionUso, UnidadMedidaPT, CostoUnitarioPT, StockPT, EstadoPT) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data['CodProducto'], data['DescripcionPT'], data.get('DescripcionUso', ''), data['UnidadMedidaPT'], data['CostoUnitarioPT'], data['StockPT'], data.get('EstadoPT', 'Activo'))
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Producto creado exitosamente"})

@app.route('/api/productos/<cod>', methods=['PUT'])
def actualizar_producto(cod):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE DIM_ProductoTerminado SET DescripcionPT=?, DescripcionUso=?, UnidadMedidaPT=?, CostoUnitarioPT=?, StockPT=?, EstadoPT=? WHERE CodProducto=?",
        (data['DescripcionPT'], data.get('DescripcionUso', ''), data['UnidadMedidaPT'], data['CostoUnitarioPT'], data['StockPT'], data.get('EstadoPT', 'Activo'), cod)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Producto actualizado"})

@app.route('/api/productos/<cod>', methods=['DELETE'])
def eliminar_producto(cod):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DIM_ProductoTerminado WHERE CodProducto=?", (cod,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Producto eliminado"})

# FÓRMULAS MAGISTRALES
@app.route('/api/formulas', methods=['GET'])
def obtener_formulas():
    conn = get_db()
    formulas = consultar(conn, "SELECT * FROM DIM_FormulaMagistral")
    conn.close()
    return jsonify(formulas)

@app.route('/api/formulas', methods=['POST'])
def crear_formula():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO DIM_FormulaMagistral (CodFormula, DescripcionFM, UnidadMedidaFM, CostoUnitarioFM, EstadoFM) VALUES (?, ?, ?, ?, ?)",
        (data['CodFormula'], data['DescripcionFM'], data['UnidadMedidaFM'], data['CostoUnitarioFM'], data.get('EstadoFM', 'Activo'))
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Fórmula creada exitosamente"})

@app.route('/api/formulas/<cod>', methods=['PUT'])
def actualizar_formula(cod):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE DIM_FormulaMagistral SET DescripcionFM=?, UnidadMedidaFM=?, CostoUnitarioFM=?, EstadoFM=? WHERE CodFormula=?",
        (data['DescripcionFM'], data['UnidadMedidaFM'], data['CostoUnitarioFM'], data.get('EstadoFM', 'Activo'), cod)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Fórmula actualizada"})

@app.route('/api/formulas/<cod>', methods=['DELETE'])
def eliminar_formula(cod):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DIM_FormulaMagistral WHERE CodFormula=?", (cod,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Fórmula eliminada"})

# CLIENTES
@app.route('/api/clientes', methods=['GET'])
def obtener_clientes():
    conn = get_db()
    clientes = consultar(conn, "SELECT * FROM DIM_Cliente")
    conn.close()
    return jsonify(clientes)

@app.route('/api/clientes/segmentacion', methods=['GET'])
def segmentacion_clientes():
    global clientes_segmentados, clusters_info
    try:
        if clientes_segmentados is None:
            clientes_segmentados, clusters_info, _ = entrenar_kmeans()
        return jsonify({
            "clientes": clientes_segmentados if clientes_segmentados else [],
            "clusters": clusters_info if clusters_info else [],
            "total": len(clientes_segmentados) if clientes_segmentados else 0
        })
    except Exception as e:
        print(f"[ERROR] segmentacion: {e}")
        return jsonify({"clientes": [], "clusters": [], "total": 0})

@app.route('/api/clientes', methods=['POST'])
def crear_cliente():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO DIM_Cliente (ClienteKey, DniCliente, NombresC, ApellidosC, FechaNacimiento, CelularC, ApoderadoC) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data['ClienteKey'], data['DniCliente'], data['NombresC'], data['ApellidosC'], data.get('FechaNacimiento'), data.get('CelularC'), data.get('ApoderadoC'))
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Cliente creado exitosamente"})

@app.route('/api/clientes/<key>', methods=['PUT'])
def actualizar_cliente(key):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE DIM_Cliente SET DniCliente=?, NombresC=?, ApellidosC=?, FechaNacimiento=?, CelularC=?, ApoderadoC=? WHERE ClienteKey=?",
        (data['DniCliente'], data['NombresC'], data['ApellidosC'], data.get('FechaNacimiento'), data.get('CelularC'), data.get('ApoderadoC'), key)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Cliente actualizado"})

@app.route('/api/clientes/<key>', methods=['DELETE'])
def eliminar_cliente(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DIM_Cliente WHERE ClienteKey=?", (key,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Cliente eliminado"})

# MÉDICOS
@app.route('/api/medicos', methods=['GET'])
def obtener_medicos():
    conn = get_db()
    medicos = consultar(conn, "SELECT * FROM DIM_Medico")
    conn.close()
    return jsonify(medicos)

@app.route('/api/medicos', methods=['POST'])
def crear_medico():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO DIM_Medico (MedicoKey, ColegiaturaMedico, NombresM, ApellidosM, CelularM, EstadoM) VALUES (?, ?, ?, ?, ?, ?)",
        (data['MedicoKey'], data['ColegiaturaMedico'], data['NombresM'], data['ApellidosM'], data.get('CelularM'), data.get('EstadoM', 'Activo'))
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Médico creado exitosamente"})

@app.route('/api/medicos/<key>', methods=['PUT'])
def actualizar_medico(key):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE DIM_Medico SET ColegiaturaMedico=?, NombresM=?, ApellidosM=?, CelularM=?, EstadoM=? WHERE MedicoKey=?",
        (data['ColegiaturaMedico'], data['NombresM'], data['ApellidosM'], data.get('CelularM'), data.get('EstadoM', 'Activo'), key)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Médico actualizado"})

@app.route('/api/medicos/<key>', methods=['DELETE'])
def eliminar_medico(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DIM_Medico WHERE MedicoKey=?", (key,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Médico eliminado"})

# SEDES
@app.route('/api/sedes', methods=['GET'])
def obtener_sedes():
    conn = get_db()
    sedes = consultar(conn, "SELECT * FROM DIM_Sede")
    conn.close()
    return jsonify(sedes)

@app.route('/api/sedes', methods=['POST'])
def crear_sede():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO DIM_Sede (SedeKey, NombreSede, Ciudad, Direccion, Region) VALUES (?, ?, ?, ?, ?)",
        (data['SedeKey'], data['NombreSede'], data['Ciudad'], data['Direccion'], data['Region'])
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Sede creada exitosamente"})

@app.route('/api/sedes/<key>', methods=['PUT'])
def actualizar_sede(key):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE DIM_Sede SET NombreSede=?, Ciudad=?, Direccion=?, Region=? WHERE SedeKey=?",
        (data['NombreSede'], data['Ciudad'], data['Direccion'], data['Region'], key)
    )
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Sede actualizada"})

@app.route('/api/sedes/<key>', methods=['DELETE'])
def eliminar_sede(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM DIM_Sede WHERE SedeKey=?", (key,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Sede eliminada"})

# VENTAS
@app.route('/api/ventas', methods=['GET'])
def obtener_ventas():
    conn = get_db()
    sql_fm = """
        SELECT v.CodVenta, v.CodFormula AS Codigo, f.DescripcionFM AS Producto, 
               c.NombresC + ' ' + c.ApellidosC AS Cliente, s.NombreSede AS Sede,
               v.Cantidad, v.SubTotalFM AS SubTotal, 'FM' AS Tipo
        FROM FACT_VentaFM v
        INNER JOIN DIM_FormulaMagistral f ON v.CodFormula = f.CodFormula
        INNER JOIN DIM_Cliente c ON v.ClienteKey = c.ClienteKey
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey
    """
    sql_pt = """
        SELECT v.CodVenta, v.CodProducto AS Codigo, p.DescripcionPT AS Producto,
               c.NombresC + ' ' + c.ApellidosC AS Cliente, s.NombreSede AS Sede,
               v.Cantidad, v.SubTotalPT AS SubTotal, 'PT' AS Tipo
        FROM FACT_VentaPT v
        INNER JOIN DIM_ProductoTerminado p ON v.CodProducto = p.CodProducto
        INNER JOIN DIM_Cliente c ON v.ClienteKey = c.ClienteKey
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey
    """
    ventas_fm = consultar(conn, sql_fm)
    ventas_pt = consultar(conn, sql_pt)
    conn.close()
    return jsonify(ventas_fm + ventas_pt)

@app.route('/api/ventas/dropdowns', methods=['GET'])
def ventas_dropdowns():
    conn = get_db()
    formulas = consultar(conn, "SELECT CodFormula, DescripcionFM, CostoUnitarioFM FROM DIM_FormulaMagistral WHERE EstadoFM='Activo'")
    productos = consultar(conn, "SELECT CodProducto, DescripcionPT, CostoUnitarioPT FROM DIM_ProductoTerminado WHERE EstadoPT='Activo'")
    clientes = consultar(conn, "SELECT ClienteKey, NombresC + ' ' + ApellidosC AS Nombre FROM DIM_Cliente")
    sedes = consultar(conn, "SELECT SedeKey, NombreSede FROM DIM_Sede")
    medicos = consultar(conn, "SELECT MedicoKey, NombresM + ' ' + ApellidosM AS Nombre FROM DIM_Medico WHERE EstadoM='Activo'")
    fechas_fm = consultar(conn, "SELECT FechaKey, CONVERT(VARCHAR, Fecha, 103) AS Fecha FROM DIM_Tiempo_FM")
    fechas_pt = consultar(conn, "SELECT FechaKey, CONVERT(VARCHAR, Fecha, 103) AS Fecha FROM DIM_Tiempo_PT")
    conn.close()
    return jsonify({
        "formulas": formulas,
        "productos": productos,
        "clientes": clientes,
        "sedes": sedes,
        "medicos": medicos,
        "fechas_fm": fechas_fm,
        "fechas_pt": fechas_pt
    })

@app.route('/api/ventas', methods=['POST'])
def crear_venta():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    tipo = data.get('tipo', 'FM')
    try:
        if tipo == 'FM':
            cursor.execute("""
                INSERT INTO FACT_VentaFM (CodVenta, CodFormula, FechaKey, ClienteKey, SedeKey, MedicoKey, Medidas, Cantidad, CostoUnitarioFM, SubTotalFM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['codVenta'], data['codProducto'], int(data['fechaKey']), int(data['clienteKey']),
                  int(data['sedeKey']), int(data['medicoKey']), data.get('medidas', ''), int(data['cantidad']),
                  float(data['costoUnitario']), float(data['subtotal'])))
        else:
            cursor.execute("""
                INSERT INTO FACT_VentaPT (CodVenta, CodProducto, FechaKey, ClienteKey, SedeKey, Medidas, Cantidad, CostoUnitarioPT, SubTotalPT, StockDespues)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['codVenta'], data['codProducto'], int(data['fechaKey']), int(data['clienteKey']),
                  int(data['sedeKey']), data.get('medidas', ''), int(data['cantidad']),
                  float(data['costoUnitario']), float(data['subtotal']), int(data.get('stockDespues', 0))))
        conn.commit()
        return jsonify({"exito": True, "mensaje": "Venta creada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})
    finally:
        conn.close()

@app.route('/api/ventas/<cod>/<tipo>', methods=['PUT'])
def editar_venta(cod, tipo):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        if tipo == 'FM':
            cursor.execute("""
                UPDATE FACT_VentaFM SET CodFormula=?, FechaKey=?, ClienteKey=?, SedeKey=?, MedicoKey=?, Medidas=?, Cantidad=?, CostoUnitarioFM=?, SubTotalFM=?
                WHERE CodVenta=?
            """, (data['codProducto'], int(data['fechaKey']), int(data['clienteKey']),
                  int(data['sedeKey']), int(data['medicoKey']), data.get('medidas', ''), int(data['cantidad']),
                  float(data['costoUnitario']), float(data['subtotal']), cod))
        else:
            cursor.execute("""
                UPDATE FACT_VentaPT SET CodProducto=?, FechaKey=?, ClienteKey=?, SedeKey=?, Medidas=?, Cantidad=?, CostoUnitarioPT=?, SubTotalPT=?, StockDespues=?
                WHERE CodVenta=?
            """, (data['codProducto'], int(data['fechaKey']), int(data['clienteKey']),
                  int(data['sedeKey']), data.get('medidas', ''), int(data['cantidad']),
                  float(data['costoUnitario']), float(data['subtotal']), int(data.get('stockDespues', 0)), cod))
        conn.commit()
        return jsonify({"exito": True, "mensaje": "Venta actualizada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})
    finally:
        conn.close()

@app.route('/api/ventas/<cod>/<tipo>', methods=['DELETE'])
def eliminar_venta(cod, tipo):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if tipo == 'FM':
            cursor.execute("DELETE FROM FACT_VentaFM WHERE CodVenta=?", (cod,))
        else:
            cursor.execute("DELETE FROM FACT_VentaPT WHERE CodVenta=?", (cod,))
        conn.commit()
        return jsonify({"exito": True, "mensaje": "Venta eliminada"})
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)})
    finally:
        conn.close()

# MÉTRICAS PARA DASHBOARD
@app.route('/api/metricas', methods=['GET'])
def obtener_metricas():
    conn = get_db()
    cursor = conn.cursor()
    
    # Totales de ventas
    cursor.execute("SELECT ISNULL(SUM(SubTotalFM), 0) FROM FACT_VentaFM")
    total_fm = float(cursor.fetchone()[0])
    
    cursor.execute("SELECT ISNULL(SUM(SubTotalPT), 0) FROM FACT_VentaPT")
    total_pt = float(cursor.fetchone()[0])
    
    total_ventas = total_fm + total_pt
    
    # Ventas por sede
    cursor.execute("""
        SELECT ISNULL(SUM(v.SubTotalFM), 0) FROM FACT_VentaFM v 
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey WHERE s.Ciudad = 'Juliaca'
    """)
    juliaca_fm = float(cursor.fetchone()[0])
    
    cursor.execute("""
        SELECT ISNULL(SUM(v.SubTotalPT), 0) FROM FACT_VentaPT v 
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey WHERE s.Ciudad = 'Juliaca'
    """)
    juliaca_pt = float(cursor.fetchone()[0])
    
    cursor.execute("""
        SELECT ISNULL(SUM(v.SubTotalFM), 0) FROM FACT_VentaFM v 
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey WHERE s.Ciudad = 'Puno'
    """)
    puno_fm = float(cursor.fetchone()[0])
    
    cursor.execute("""
        SELECT ISNULL(SUM(v.SubTotalPT), 0) FROM FACT_VentaPT v 
        INNER JOIN DIM_Sede s ON v.SedeKey = s.SedeKey WHERE s.Ciudad = 'Puno'
    """)
    puno_pt = float(cursor.fetchone()[0])
    
    # Conteos
    cursor.execute("SELECT COUNT(*) FROM DIM_ProductoTerminado")
    total_productos = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM DIM_FormulaMagistral")
    total_formulas = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM DIM_Cliente")
    total_clientes = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM DIM_Medico")
    total_medicos = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT COUNT(*) FROM DIM_Sede")
    total_sedes = int(cursor.fetchone()[0])
    
    cursor.execute("SELECT ISNULL(SUM(StockPT), 0) FROM DIM_ProductoTerminado")
    stock_total = int(cursor.fetchone()[0])
    
    # Ventas por mes - usando FM directo
    cursor.execute("""
        SELECT t.MesNombre, ISNULL(SUM(v.SubTotalFM), 0) AS Total
        FROM DIM_Tiempo_FM t
        INNER JOIN FACT_VentaFM v ON t.FechaKey = v.FechaKey
        GROUP BY t.MesNombre, t.Mes
        ORDER BY t.Mes
    """)
    ventas_por_mes = [{"mes": row[0], "total": float(row[1])} for row in cursor.fetchall()]
    
    # Ventas FM y PT por mes - usando tablas separadas
    cursor.execute("""
        SELECT t.MesNombre, ISNULL(SUM(v.SubTotalFM), 0) AS FM
        FROM DIM_Tiempo_FM t
        INNER JOIN FACT_VentaFM v ON t.FechaKey = v.FechaKey
        GROUP BY t.MesNombre, t.Mes
        ORDER BY t.Mes
    """)
    ventas_fm = [{"mes": row[0], "total": float(row[1])} for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT t.MesNombre, ISNULL(SUM(v.SubTotalPT), 0) AS PT
        FROM DIM_Tiempo_PT t
        INNER JOIN FACT_VentaPT v ON t.FechaKey = v.FechaKey
        GROUP BY t.MesNombre, t.Mes
        ORDER BY t.Mes
    """)
    ventas_pt = [{"mes": row[0], "total": float(row[1])} for row in cursor.fetchall()]
    
    # Combinar FM y PT por mes
    meses_fm = {v['mes']: v['total'] for v in ventas_fm}
    meses_pt = {v['mes']: v['total'] for v in ventas_pt}
    todos_los_meses = list(dict.fromkeys(list(meses_fm.keys()) + list(meses_pt.keys())))
    ventas_fm_pt_mes = [{"mes": m, "fm": meses_fm.get(m, 0), "pt": meses_pt.get(m, 0)} for m in todos_los_meses]
    
    # Ventas por sede
    cursor.execute("""
        SELECT s.NombreSede, ISNULL(SUM(v.SubTotalFM), 0) AS Total
        FROM DIM_Sede s
        INNER JOIN FACT_VentaFM v ON s.SedeKey = v.SedeKey
        GROUP BY s.NombreSede
    """)
    sedes_fm = {row[0]: float(row[1]) for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT s.NombreSede, ISNULL(SUM(v.SubTotalPT), 0) AS Total
        FROM DIM_Sede s
        INNER JOIN FACT_VentaPT v ON s.SedeKey = v.SedeKey
        GROUP BY s.NombreSede
    """)
    sedes_pt = {row[0]: float(row[1]) for row in cursor.fetchall()}
    
    # Combinar sedes
    todas_sedes = list(dict.fromkeys(list(sedes_fm.keys()) + list(sedes_pt.keys())))
    ventas_sede_resumen = [{"sede": s, "fm": sedes_fm.get(s, 0), "pt": sedes_pt.get(s, 0)} for s in todas_sedes]
    
    conn.close()
    
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
        "total_productos": total_productos,
        "total_formulas": total_formulas,
        "total_clientes": total_clientes,
        "total_medicos": total_medicos,
        "total_sedes": total_sedes,
        "stock_total": stock_total,
        "ventas_por_mes": ventas_por_mes,
        "ventas_fm_pt_mes": ventas_fm_pt_mes,
        "ventas_sede_resumen": ventas_sede_resumen
    })

if __name__ == '__main__':
    print("[API] Servidor iniciado en http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
