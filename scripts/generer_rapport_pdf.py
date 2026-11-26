"""Convertit ``docs/rapport.md`` en ``docs/rapport.pdf`` (reportlab).

Convertisseur Markdown minimal, suffisant pour le rapport : titres,
paragraphes, listes à puces, tableaux, blocs de code, images, gras,
italique, code en ligne et sauts de page (``<!-- pagebreak -->``).
Le texte placé avant le premier saut de page forme la page de garde.

Nécessite reportlab (outil de documentation uniquement).

Utilisation ::

    python scripts/generer_rapport_pdf.py
"""

import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(RACINE, "docs")
SOURCE = os.path.join(DOCS, "rapport.md")
SORTIE = os.path.join(DOCS, "rapport.pdf")
TITRE_COURANT = "Mini-projet 1 — Gestion d'une bibliothèque universitaire"
BLEU = colors.HexColor("#1F4E79")


def enregistrer_polices():
    """Enregistre Calibri/Consolas si disponibles ; retourne les noms."""
    dossier = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    fichiers = {
        "Texte": "calibri.ttf", "Texte-Gras": "calibrib.ttf",
        "Texte-Italique": "calibrii.ttf", "Texte-GrasItalique": "calibriz.ttf",
        "Code": "consola.ttf",
    }
    if not all(os.path.exists(os.path.join(dossier, f))
               for f in fichiers.values()):
        return "Helvetica", "Courier"
    for nom, fichier in fichiers.items():
        pdfmetrics.registerFont(TTFont(nom, os.path.join(dossier, fichier)))
    pdfmetrics.registerFontFamily(
        "Texte", normal="Texte", bold="Texte-Gras",
        italic="Texte-Italique", boldItalic="Texte-GrasItalique")
    return "Texte", "Code"


TEXTE, CODE = enregistrer_polices()
STYLES = {
    "corps": ParagraphStyle("corps", fontName=TEXTE, fontSize=10.5,
                            leading=14, alignment=TA_JUSTIFY,
                            spaceAfter=5),
    "puce": ParagraphStyle("puce", fontName=TEXTE, fontSize=10.5,
                           leading=13.5, leftIndent=14, bulletIndent=4,
                           spaceAfter=2.5, alignment=TA_JUSTIFY),
    "h1": ParagraphStyle("h1", fontName=TEXTE, fontSize=15, leading=19,
                         textColor=BLEU, spaceBefore=10, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName=TEXTE, fontSize=12, leading=15,
                         textColor=BLEU, spaceBefore=7, spaceAfter=4),
    "cellule": ParagraphStyle("cellule", fontName=TEXTE, fontSize=9.5,
                              leading=11.5),
    "code": ParagraphStyle("code", fontName=CODE, fontSize=8.3,
                           leading=10.2, backColor=colors.HexColor(
                               "#F4F6F8"), borderPadding=5,
                           leftIndent=5, rightIndent=5, spaceBefore=4,
                           spaceAfter=9),
    "garde_titre": ParagraphStyle("gt", fontName=TEXTE, fontSize=30,
                                  leading=36, alignment=TA_CENTER,
                                  textColor=BLEU, spaceAfter=14),
    "garde_sous_titre": ParagraphStyle("gst", fontName=TEXTE, fontSize=20,
                                       leading=26, alignment=TA_CENTER,
                                       spaceAfter=30),
    "garde": ParagraphStyle("g", fontName=TEXTE, fontSize=12.5,
                            leading=18, alignment=TA_CENTER,
                            spaceAfter=12),
}


def en_ligne(texte):
    """Convertit la mise en forme Markdown en ligne vers le balisage
    reportlab (gras, italique, code, liens)."""
    texte = (texte.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))
    morceaux = re.split(r"(`[^`]+`)", texte)
    resultat = []
    for morceau in morceaux:
        if morceau.startswith("`") and morceau.endswith("`"):
            resultat.append(f'<font name="{CODE}" size="9">'
                            f"{morceau[1:-1]}</font>")
            continue
        morceau = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", morceau)
        morceau = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])",
                         r"<i>\1</i>", morceau)
        morceau = re.sub(r"(https?://[^\s<]+)",
                         r'<link href="\1" color="#1F4E79">\1</link>',
                         morceau)
        resultat.append(morceau)
    return "".join(resultat)


def tableau(lignes, largeur):
    """Construit un tableau à partir de lignes Markdown ``| a | b |``."""
    cellules = [[c.strip() for c in ligne.strip().strip("|").split("|")]
                for ligne in lignes
                if not re.match(r"^\|\s*:?-+", ligne.strip())]
    donnees = [[Paragraph(("<b>%s</b>" if i == 0 else "%s") % en_ligne(c),
                          STYLES["cellule"]) for c in rangee]
               for i, rangee in enumerate(cellules)]
    nb = len(cellules[0])
    # Les colonnes de code (`...`) ne doivent pas être coupées : leur
    # largeur minimale correspond à leur plus long contenu.
    longueurs = [max(len(r[i]) for r in cellules) for i in range(nb)]
    minimums = [max((len(r[i]) for r in cellules[1:]
                     if r[i].startswith("`")), default=0) * 0.205 * cm
                for i in range(nb)]
    total = sum(longueurs)
    largeurs = [max(largeur * max(0.14, n / total), m)
                for n, m in zip(longueurs, minimums)]
    facteur = largeur / sum(largeurs)
    table = Table(donnees, colWidths=[w * facteur for w in largeurs],
                  repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA7B4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def convertir(markdown, largeur, hauteur):
    """Transforme le texte Markdown en liste de flowables reportlab."""
    elements = []
    lignes = markdown.splitlines()
    garde = True
    paragraphe = []
    i = 0

    def vider():
        if paragraphe:
            style = STYLES["garde"] if garde else STYLES["corps"]
            elements.append(Paragraph(en_ligne(" ".join(paragraphe)),
                                      style))
            paragraphe.clear()

    while i < len(lignes):
        ligne = lignes[i]
        brut = ligne.strip()
        if brut == "<!-- pagebreak -->":
            vider()
            elements.append(PageBreak())
            garde = False
        elif not brut:
            vider()
        elif brut.startswith("```"):
            vider()
            bloc = []
            i += 1
            while i < len(lignes) and not lignes[i].strip().startswith("```"):
                bloc.append(lignes[i])
                i += 1
            elements.append(Preformatted("\n".join(bloc), STYLES["code"]))
        elif brut.startswith("|"):
            vider()
            bloc = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                bloc.append(lignes[i])
                i += 1
            elements.append(tableau(bloc, largeur))
            elements.append(Spacer(1, 7))
            continue
        elif brut.startswith("!["):
            vider()
            chemin = os.path.join(DOCS, re.search(r"\((.+?)\)", brut)
                                  .group(1))
            image = Image(chemin)
            echelle = min(largeur / image.imageWidth,
                          hauteur * 0.62 / image.imageHeight)
            image.drawWidth = image.imageWidth * echelle
            image.drawHeight = image.imageHeight * echelle
            elements.append(image)
            elements.append(Spacer(1, 8))
        elif brut.startswith("# "):
            vider()
            if garde:
                elements.append(Spacer(1, 5 * cm))
            elements.append(Paragraph(en_ligne(brut[2:]),
                                      STYLES["garde_titre"]))
        elif brut.startswith("## "):
            vider()
            style = STYLES["garde_sous_titre"] if garde else STYLES["h1"]
            elements.append(Paragraph(en_ligne(brut[3:]), style))
        elif brut.startswith("### "):
            vider()
            elements.append(Paragraph(en_ligne(brut[4:]), STYLES["h2"]))
        elif brut.startswith("- "):
            vider()
            elements.append(Paragraph(en_ligne(brut[2:]), STYLES["puce"],
                                      bulletText="•"))
        else:
            paragraphe.append(brut)
        i += 1
    vider()
    return elements


def decorer_page(canvas, document):
    """Ajoute en-tête et numéro de page (sauf sur la page de garde)."""
    document.nb_pages = canvas.getPageNumber()
    if canvas.getPageNumber() == 1:
        return
    canvas.saveState()
    canvas.setFont(TEXTE, 8.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    largeur, hauteur = A4
    canvas.drawString(2 * cm, hauteur - 1.3 * cm, TITRE_COURANT)
    canvas.drawRightString(largeur - 2 * cm, hauteur - 1.3 * cm,
                           "ALLE Sourou Marcel")
    canvas.line(2 * cm, hauteur - 1.45 * cm, largeur - 2 * cm,
                hauteur - 1.45 * cm)
    canvas.drawCentredString(largeur / 2, 1.2 * cm,
                             f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def generer():
    """Produit le PDF et retourne ``(chemin, nombre de pages)``."""
    document = SimpleDocTemplate(
        SORTIE, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=1.9 * cm,
        title="Rapport — Gestion d'une bibliothèque universitaire",
        author="ALLE Sourou Marcel")
    with open(SOURCE, encoding="utf-8") as fichier:
        elements = convertir(fichier.read(), document.width,
                             document.height)
    document.build(elements, onFirstPage=decorer_page,
                   onLaterPages=decorer_page)
    return SORTIE, document.nb_pages


if __name__ == "__main__":
    chemin, pages = generer()
    print(f"Rapport généré : {chemin} ({pages} pages)")
