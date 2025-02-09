import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px  # Ajout de Plotly pour les graphiques interactifs
from fpdf import FPDF
import sqlite3
import base64
import os


# Connexion à la base de données SQLite
conn = sqlite3.connect("factures.db")
cursor = conn.cursor()

# Création des tables si elles n'existent pas
cursor.execute("""
CREATE TABLE IF NOT EXISTS Factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    client_name TEXT,
    produits TEXT,
    total REAL,
    tva REAL,
    css REAL,
    montant_ttc REAL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS Ventes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    produit TEXT,
    montant REAL
)
""")
conn.commit()

# Vérifier si les colonnes existent déjà dans la table 'Factures'
cursor.execute("PRAGMA table_info(Factures)")
columns = [column[1] for column in cursor.fetchall()]

if "tva" not in columns:
    cursor.execute("ALTER TABLE Factures ADD COLUMN tva REAL")
    conn.commit()

if "css" not in columns:
    cursor.execute("ALTER TABLE Factures ADD COLUMN css REAL")
    conn.commit()

if "montant_ttc" not in columns:
    cursor.execute("ALTER TABLE Factures ADD COLUMN montant_ttc REAL")
    conn.commit()

# Vérifier si la colonne 'produit' existe déjà dans la table 'Ventes'
cursor.execute("PRAGMA table_info(Ventes)")
columns = [column[1] for column in cursor.fetchall()]

if "produit" not in columns:
    cursor.execute("ALTER TABLE Ventes ADD COLUMN produit TEXT")
    conn.commit()


# Fonction pour créer un PDF
class FacturePDF(FPDF):
    def header(self):
        # Entête de la facture avec les coordonnées de l'entreprise
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Entreprise XYZ", ln=True, align="C")
        self.cell(0, 10, "Adresse : 123 Rue de l'Exemple, Ville", ln=True, align="C")
        self.cell(0, 10, "Téléphone : +225 123 456 789", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_facture_details(self, data):
        self.set_font("Arial", "", 10)
        col_width = 40
        row_height = 10
        for row in data:
            for item in row:
                self.cell(col_width, row_height, str(item), border=1)
            self.ln(row_height)


# Fonction pour enregistrer la facture au format PDF
def generate_pdf(facture_data, filename, client_name):
    pdf = FacturePDF()
    pdf.add_page()
    
    # Ajouter le nom du client en haut du PDF
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Client : {client_name}", ln=True, align="L")
    pdf.ln(10)

    pdf.add_facture_details(facture_data)
    pdf.output(filename)


# Fonction pour encoder le fichier PDF en base64 (pour le téléchargement)
def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Télécharger {file_label}</a>'
    return href


# Initialisation de l'état de session
if "produits" not in st.session_state:
    st.session_state.produits = []
if "total" not in st.session_state:
    st.session_state.total = 0
if "ajout_produit_visible" not in st.session_state:
    st.session_state.ajout_produit_visible = False
if "page" not in st.session_state:
    st.session_state.page = 1  # Compteur de page initialisé à 1


# Personnalisation des couleurs avec CSS
st.markdown(
    """
    <style>
        .stApp {
            background-color: #f8f9fa; /* Couleur de fond */
        }
        h1, h2, h3 {
            color: #343a40; /* Couleur des titres */
        }
        .stButton>button {
            background-color: #007bff; /* Bleu pour les boutons */
            color: white;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #0056b3; /* Effet hover sur les boutons */
        }
        .stTable tbody tr:nth-child(even) {
            background-color: #e9ecef; /* Alternance de couleur dans les tableaux */
        }
        .stTable tbody tr:nth-child(odd) {
            background-color: #ffffff;
        }
        .stMarkdown {
            text-align: center; /* Centrer les textes */
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# Interface Streamlit
st.title("Gestion de Factures et Analyse des Données ∶")

# Menu structuré avec onglets
selected_option = st.sidebar.selectbox(
    "Menu",
    ["Créer une Facture", "Historique des Factures", "Analyse des Données"],
    format_func=lambda x: f"∶ {x} ∶"
)

if selected_option == "Créer une Facture":
    # Partie 1 : Création de factures
    st.header("∶ Créer une Facture ∶")
    col_client, col_produits = st.columns([1, 2])

    with col_client:
        type_facture = st.selectbox("∶ Type de Facture ∶", ["Proforma", "Définitive"])
        client_name = st.text_input("∶ Nom du Client ∶")

    with col_produits:
        if st.button("∶ Ajouter un Produit ∶", key="add_product"):
            st.session_state.ajout_produit_visible = True

        if st.session_state.ajout_produit_visible:
            with st.form(key="form_ajout_produit"):
                produit = {}
                produit["nom"] = st.text_input("∶ Nom du Produit ∶", key="nom_produit")
                produit["quantite"] = st.number_input("∶ Quantité ∶", min_value=1, value=1, key="quantite")
                produit["prix_unitaire"] = st.number_input("∶ Prix Unitaire (FCFA) ∶", min_value=0.0, value=0.0, key="prix_unitaire")
                submitted = st.form_submit_button("∶ Valider Produit ∶")
                if submitted:
                    if produit["nom"] and produit["prix_unitaire"] > 0:
                        produit["montant"] = produit["quantite"] * produit["prix_unitaire"]
                        st.session_state.total += produit["montant"]
                        st.session_state.produits.append(produit)
                        st.session_state.ajout_produit_visible = False
                    else:
                        st.warning("∶ Veuillez remplir tous les champs correctement ∶")

    if st.session_state.produits:
        col_details, col_actions = st.columns([2, 1])
        with col_details:
            st.write("∶ Détails des Produits ∶")
            df_produits = pd.DataFrame(st.session_state.produits)
            st.table(df_produits[["nom", "quantite", "prix_unitaire", "montant"]])

            # Calcul des taxes
            tva = st.session_state.total * 0.18  # 18%
            css = st.session_state.total * 0.01  # 1%
            total_ttc = st.session_state.total + tva + css

            st.write(f"∶ Total HT ∶ {st.session_state.total:.2f} FCFA")
            st.write(f"∶ TVA (18%) ∶ {tva:.2f} FCFA")
            st.write(f"∶ CSS (1%) ∶ {css:.2f} FCFA")
            st.write(f"∶ Total TTC ∶ {total_ttc:.2f} FCFA")

        with col_actions:
            # Bouton pour enregistrer la facture dans la base de données
            if st.button("∶ Enregistrer Facture ∶", key="enregistrer"):
                if not client_name or not st.session_state.produits:
                    st.warning("∶ Veuillez remplir tous les champs nécessaires ∶")
                else:
                    produits_str = str(st.session_state.produits)  # Convertir la liste de produits en string
                    
                    # Calcul des taxes
                    tva = st.session_state.total * 0.18  # 18%
                    css = st.session_state.total * 0.01  # 1%
                    total_ttc = st.session_state.total + tva + css
                    
                    cursor.execute("""
                        INSERT INTO Factures (type, client_name, produits, total, tva, css, montant_ttc)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (type_facture, client_name, produits_str, st.session_state.total, tva, css, total_ttc))
                    
                    # Enregistrer chaque produit dans la table Ventes
                    for produit in st.session_state.produits:
                        cursor.execute("""
                            INSERT INTO Ventes (date, produit, montant)
                            VALUES (?, ?, ?)
                        """, (pd.Timestamp.now().date(), produit["nom"], produit["montant"]))
                    
                    conn.commit()
                    st.success(f"∶ Facture {type_facture} enregistrée avec succès ! ∶")

            # Bouton pour générer le PDF
            if st.button("∶ Générer PDF ∶", key="pdf"):
                if not client_name:
                    st.warning("∶ Veuillez entrer le nom du client ∶")
                elif not st.session_state.produits:
                    st.warning("∶ Veuillez ajouter au moins un produit ∶")
                else:
                    # Calcul des taxes
                    tva = st.session_state.total * 0.18  # 18%
                    css = st.session_state.total * 0.01  # 1%
                    total_ttc = st.session_state.total + tva + css

                    # Préparer les données pour le PDF
                    facture_data = [["Description", "Quantité", "Prix Unitaire (FCFA)", "Montant (FCFA)"]]
                    for produit in st.session_state.produits:
                        facture_data.append([produit["nom"], produit["quantite"], f"{produit['prix_unitaire']:.2f}", f"{produit['montant']:.2f}"])

                    facture_data.append(["", "", "Total HT", f"{st.session_state.total:.2f} FCFA"])
                    facture_data.append(["", "", "TVA (18%)", f"{tva:.2f} FCFA"])
                    facture_data.append(["", "", "CSS (1%)", f"{css:.2f} FCFA"])
                    facture_data.append(["", "", "Total TTC", f"{total_ttc:.2f} FCFA"])

                    # Générer et télécharger le PDF
                    filename = f"facture_{type_facture.lower()}.pdf"
                    generate_pdf(facture_data, filename, client_name)
                    st.success(f"∶ Facture {type_facture} générée avec succès ! ∶")
                    st.markdown(get_binary_file_downloader_html(filename, f"∶ Facture {type_facture} ∶"), unsafe_allow_html=True)

            # Bouton pour réinitialiser les données pour une nouvelle facture
            if st.button("∶ Nouvelle Facture ∶", key="nouvelle_facture"):
                st.session_state.produits = []
                st.session_state.total = 0
                st.info("∶ Les données de la facture ont été réinitialisées. Vous pouvez créer une nouvelle facture. ∶")

elif selected_option == "Historique des Factures":
    # Partie 2 : Historique des factures avec pagination
    st.header("∶ Historique des Factures ∶")

    # Récupérer toutes les factures
    cursor.execute("SELECT id, type, client_name, total, tva, css, montant_ttc FROM Factures")
    factures = cursor.fetchall()

    if factures:
        # Nombre d'éléments par page
        items_per_page = 10
        start_idx = (st.session_state.page - 1) * items_per_page
        end_idx = st.session_state.page * items_per_page

        # Filtrer les factures pour la page actuelle
        paginated_factures = factures[start_idx:end_idx]

        # Formater les montants avec deux décimales et gérer les valeurs None
        formatted_factures = []
        for facture in paginated_factures:
            total_ht = facture[3] if facture[3] is not None else 0.0
            tva = facture[4] if facture[4] is not None else 0.0
            css = facture[5] if facture[5] is not None else 0.0
            montant_ttc = facture[6] if facture[6] is not None else 0.0

            formatted_facture = list(facture[:3])  # Conserver les trois premières colonnes (ID, Type, Client)
            formatted_facture.append(f"{total_ht:.2f}")  # Total HT
            formatted_facture.append(f"{tva:.2f}")  # TVA
            formatted_facture.append(f"{css:.2f}")  # CSS
            formatted_facture.append(f"{montant_ttc:.2f}")  # Montant TTC
            formatted_factures.append(formatted_facture)

        # Afficher les factures paginées
        df_factures = pd.DataFrame(formatted_factures, columns=["ID", "Type", "Client", "Total HT (FCFA)", "TVA (FCFA)", "CSS (FCFA)", "Montant TTC (FCFA)"])
        st.table(df_factures)

        # Pagination
        total_pages = (len(factures) + items_per_page - 1) // items_per_page
        col_prev, col_next = st.columns([1, 1])

        with col_prev:
            if st.button("∶ Previous ∶") and st.session_state.page > 1:
                st.session_state.page -= 1

        with col_next:
            if st.button("∶ Next ∶") and st.session_state.page < total_pages:
                st.session_state.page += 1

        st.write(f"∶ Page {st.session_state.page} sur {total_pages} ∶")

        # Rechercher une facture par ID
        facture_id = st.number_input("∶ Rechercher une facture par ID ∶", min_value=1, value=1)
        if st.button("∶ Chercher Facture ∶"):
            cursor.execute("SELECT * FROM Factures WHERE id=?", (facture_id,))
            facture = cursor.fetchone()
            if facture:
                produits = eval(facture[3]) if facture[3] else []  # Récupérer les produits sous forme de liste
                
                # Remplacer les valeurs None par 0.0
                total_ht = f"{facture[4]:.2f}" if facture[4] is not None else "0.00"
                tva = f"{facture[5]:.2f}" if facture[5] is not None else "0.00"
                css = f"{facture[6]:.2f}" if facture[6] is not None else "0.00"
                montant_ttc = f"{facture[7]:.2f}" if facture[7] is not None else "0.00"

                st.write(f"∶ Facture trouvée ∶ Type={facture[1]}, Client={facture[2]}")
                st.write(f"∶ Total HT ∶ {total_ht} FCFA")
                st.write(f"∶ TVA (18%) ∶ {tva} FCFA")
                st.write(f"∶ CSS (1%) ∶ {css} FCFA")
                st.write(f"∶ Montant TTC ∶ {montant_ttc} FCFA")
                st.table(pd.DataFrame(produits))
            else:
                st.warning("∶ Aucune facture correspondante ∶")
    else:
        st.info("∶ Aucune facture enregistrée ∶")

elif selected_option == "Analyse des Données":
    # Partie 3 : Visualisation des ventes
    st.header("∶ Analyse des Données ∶")
    col_graph1, col_graph2 = st.columns([1, 1])

    with col_graph1:
        # Afficher toutes les ventes
        cursor.execute("SELECT date, produit, montant FROM Ventes")
        ventes_data = cursor.fetchall()

        if ventes_data:
            df_ventes = pd.DataFrame(ventes_data, columns=["Date", "Produit", "Montant (FCFA)"])
            df_ventes["Date"] = pd.to_datetime(df_ventes["Date"])

            st.write("∶ Données des ventes ∶")
            st.table(df_ventes)

            # Graphique interactif des ventes par produit
            st.subheader("∶ Ventes par Produit ∶")
            grouped_by_produit = df_ventes.groupby("Produit", as_index=False).agg({"Montant (FCFA)": "sum"})
            fig = px.bar(
                grouped_by_produit,
                x="Produit",
                y="Montant (FCFA)",
                title="∶ Répartition des ventes par produit ∶",
                labels={"Montant (FCFA)": "∶ Montant Total (FCFA) ∶"}
            )
            fig.update_layout(xaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig)

    with col_graph2:
        # Graphique des ventes dans le temps
        st.subheader("∶ Évolution des Ventes dans le Temps ∶")
        df_ventes["Date"] = df_ventes["Date"].dt.strftime("%Y-%m-%d")  # Convertir en string pour Plotly
        fig2 = px.line(
            df_ventes,
            x="Date",
            y="Montant (FCFA)",
            color="Produit",
            title="∶ Évolution des ventes par produit ∶"
        )
        st.plotly_chart(fig2)

    if not ventes_data:
        st.info("∶ Aucune donnée de vente disponible ∶")


# Fermer la connexion à la base de données
conn.close()