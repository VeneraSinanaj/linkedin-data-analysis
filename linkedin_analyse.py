import os
import locale
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------
# Paramètres généraux
# ---------------------------------------------------------

# À adapter si le dossier change

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

# Mois en français avec majuscule
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "")


# ---------------------------------------------------------
# Utilitaires de formatage de dates
# ---------------------------------------------------------

def format_date(dt):
    if pd.isna(dt) or dt is None:
        return "-"
    try:
        mois_fr = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        mois = mois_fr[dt.month - 1]
        return f"{dt.day:02d} {mois} {dt.year}"
    except Exception:
        return str(dt)


def format_datetime(dt):
    if pd.isna(dt) or dt is None:
        return "-"
    try:
        mois_fr = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        mois = mois_fr[dt.month - 1]
        return f"{dt.day:02d} {mois} {dt.year} à {dt.hour}h{dt.minute:02d}"
    except Exception:
        return str(dt)


# ---------------------------------------------------------
# Chargement & détection automatique des fichiers
# ---------------------------------------------------------

def safe_load_csv(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"Erreur de lecture du fichier {path} : {e}")
        return None


def safe_prepare_dates(df, col="Date"):
    """
    Garantit que le DataFrame possède une colonne Date exploitable.
    - Si df est None, vide ou sans colonne Date → retourne un DF vide structuré
    - Sinon → convertit la colonne Date proprement
    """
    if df is None or df.empty or col not in df.columns:
        return pd.DataFrame({col: pd.to_datetime([])})

    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def preprocess_interactions(df, source_name):
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    df["year_month"] = df["Date"].dt.to_period("M")
    df["hour"] = df["Date"].dt.hour

    try:
        df["weekday"] = df["Date"].dt.day_name(locale="fr_FR").str.lower()
    except TypeError:
        df["weekday"] = df["Date"].dt.day_name().str.lower()

    df["month"] = df["Date"].dt.month
    df["type"] = source_name
    return df


def detect_and_load_data(data_dir):
    expected_files = [
        "Reactions", "Comments", "Positions", "Connections",
        "Profile", "Profile Summary", "Messages", "Logins", "Events"
    ]

    files_info = {}
    for name in expected_files:
        path_csv = os.path.join(data_dir, f"{name}.csv")
        files_info[name] = os.path.exists(path_csv)

    # Chargement des fichiers
    reactions = safe_load_csv(os.path.join(data_dir, "Reactions.csv"))
    comments = safe_load_csv(os.path.join(data_dir, "Comments.csv"))
    positions = safe_load_csv(os.path.join(data_dir, "Positions.csv"))
    connections = safe_load_csv(os.path.join(data_dir, "Connections.csv"))
    saved_jobs = safe_load_csv(os.path.join(data_dir, "jobs", "Saved Jobs.csv"))

    # Sécurisation des colonnes Date AVANT tout traitement
    reactions = safe_prepare_dates(reactions)
    comments = safe_prepare_dates(comments)

    # Préprocessing interactions
    if not reactions.empty:
        reactions = preprocess_interactions(reactions, "Reactions")

    if not comments.empty:
        comments = preprocess_interactions(comments, "Comments")

    # Préprocessing connections
    if connections is not None:
        connections = connections.copy()
        connections.columns = connections.columns.str.strip()

        if "Connected On" in connections.columns:
            connections["Connected On"] = pd.to_datetime(connections["Connected On"], errors="coerce")
            connections = connections.dropna(subset=["Connected On"])
            connections = connections.sort_values("Connected On")
        else:
            print("❌ Colonne 'Connected On' absente dans Connections.csv")

    # Fusion réactions + commentaires
    if not reactions.empty and not comments.empty:
        df_all = pd.concat([reactions, comments], ignore_index=True)
    elif not reactions.empty:
        df_all = reactions.copy()
    elif not comments.empty:
        df_all = comments.copy()
    else:
        df_all = None

    # Comptage activité
    if df_all is not None and not df_all.empty:
        activity_counts = df_all.groupby(["year_month", "type"]).size().unstack(fill_value=0)
        activity_counts.index = activity_counts.index.to_timestamp()
    else:
        activity_counts = None

    # Timeline parcours pro
    events = []
    if positions is not None and "Started On" in positions.columns:
        positions = positions.copy()
        positions["Started On"] = pd.to_datetime(positions["Started On"], errors="coerce")
        for _, row in positions.iterrows():
            if pd.notnull(row["Started On"]):
                title = row.get("Title", "Poste")
                events.append((row["Started On"], f"Début poste : {title}"))

    return {
        "reactions": reactions,
        "comments": comments,
        "positions": positions,
        "connections": connections,
        "saved_jobs": saved_jobs,
        "df_all": df_all,
        "activity_counts": activity_counts,
        "events": events,
        "files_info": files_info,
    }

# ---------------------------------------------------------
# Graphiques : évolution mensuelle & cumulée
# ---------------------------------------------------------

def plot_monthly_activity(activity_counts, events):
    if activity_counts is None or activity_counts.empty:
        messagebox.showwarning("Données manquantes", "Aucune donnée agrégée par mois disponible.")
        return

    col_reactions = next((c for c in activity_counts.columns if "reaction" in c.lower()), None)
    col_comments = next((c for c in activity_counts.columns if "comment" in c.lower()), None)

    plt.figure(figsize=(12, 6))
    if col_reactions:
        plt.plot(activity_counts.index, activity_counts[col_reactions], label="Réactions", marker="o")
    if col_comments:
        plt.plot(activity_counts.index, activity_counts[col_comments], label="Commentaires", marker="o")

    for date, label in events:
        plt.axvline(date, color="gray", linestyle="--", alpha=0.5)
        plt.text(date, plt.ylim()[1], label, rotation=90, fontsize=8)

    plt.title("Évolution de mon activité LinkedIn")
    plt.xlabel("Mois")
    plt.ylabel("Interactions")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    
    # Calcul du total par mois
    monthly_totals = activity_counts.sum(axis=1)

    # Mois le plus actif
    best_month = monthly_totals.idxmax()
    best_value = monthly_totals.max()

    # Mois le moins actif
    worst_month = monthly_totals.idxmin()
    worst_value = monthly_totals.min()

    # Formatage des dates (ex : "mars 2024")
    best_month_str = best_month.strftime("%B %Y")
    worst_month_str = worst_month.strftime("%B %Y")

    # Construction du message intelligent
    message = (
        f"Mois le plus actif : {best_month_str} ({best_value} interactions).\n"
        f"Mois le moins actif : {worst_month_str} ({worst_value} interactions).\n\n"
        )

    # Commentaire qualitatif
    if best_value == 0:
        message += "Vous n'avez eu aucune activité sur toute la période."
    elif best_value < 10:
        message += "Votre activité est globalement faible, mais régulière."
    elif best_value < 30:
        message += "Votre activité est correcte, avec quelques pics intéressants."
    else:
        message += "Très belle activité ! Vous avez eu un mois particulièrement dynamique."

    # Affichage dans une popup
    messagebox.showinfo("Analyse mensuelle", message)


def plot_cumulative_activity(df_all, events):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour l'activité cumulée.")
        return

    df = df_all.copy()
    df["count"] = 1
    cumulative = df.groupby(["Date", "type"])["count"].sum().unstack(fill_value=0).sort_index().cumsum()

    col_reactions = next((c for c in cumulative.columns if "reaction" in c.lower()), None)
    col_comments = next((c for c in cumulative.columns if "comment" in c.lower()), None)

    plt.figure(figsize=(12, 6))
    if col_reactions:
        plt.plot(cumulative.index, cumulative[col_reactions], label="Réactions cumulées")
    if col_comments:
        plt.plot(cumulative.index, cumulative[col_comments], label="Commentaires cumulés")

    for date, label in events:
        plt.axvline(date, color="gray", linestyle="--", alpha=0.5)
        plt.text(date, plt.ylim()[1], label, rotation=90, fontsize=8)

    plt.title("Activité cumulée sur LinkedIn")
    plt.xlabel("Date")
    plt.ylabel("Total interactions")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    show_cumulative_comment(cumulative.resample("M").sum())
    
def show_cumulative_comment(activity_counts):
    """
    Analyse la régularité de l'activité et affiche un message intelligent avec emojis.
    """

    # Total par mois
    monthly_totals = activity_counts.sum(axis=1)

    # Variation absolue entre mois successifs
    diffs = monthly_totals.diff().abs().dropna()

    # Indicateur de régularité
    mean_variation = diffs.mean()

    # Mois extrêmes
    best_month = monthly_totals.idxmax()
    worst_month = monthly_totals.idxmin()

    best_month_str = best_month.strftime("%B %Y")
    worst_month_str = worst_month.strftime("%B %Y")

    # Message principal
    message = (
        f"**Mois le plus actif :** {best_month_str} ({monthly_totals.max()} interactions)\n"
        f"**Mois le moins actif :** {worst_month_str} ({monthly_totals.min()} interactions)\n\n"
    )

    # Commentaire basé sur la régularité
    if mean_variation < 5:
        message += "Votre activité est **très régulière**. Vous interagissez de manière stable chaque mois."
    elif mean_variation < 15:
        message += "Votre activité est **plutôt régulière**, avec quelques variations normales."
    elif mean_variation < 30:
        message += "Votre activité montre des **variations importantes**. Vous alternez entre périodes calmes et actives."
    else:
        message += "Votre activité est **très irrégulière**, avec de fortes fluctuations d'un mois à l'autre."

    # Popup Tkinter
    messagebox.showinfo("Analyse cumulative — Régularité", message)

# ---------------------------------------------------------
# Analyses : pics d'activité
# ---------------------------------------------------------
def show_activity_peaks_page(reactions, comments):
    if reactions is None and comments is None:
        messagebox.showwarning("Données manquantes", "Aucune donnée de réactions ni de commentaires disponible.")
        return

    reactions = reactions if reactions is not None else pd.DataFrame(columns=["Date"])
    comments = comments if comments is not None else pd.DataFrame(columns=["Date"])

    daily_likes = reactions.groupby(reactions["Date"].dt.date).size()
    daily_comments = comments.groupby(comments["Date"].dt.date).size()
    daily_total = daily_likes.add(daily_comments, fill_value=0)

    if daily_total.empty:
        messagebox.showinfo("Information", "Pas de données suffisantes pour les pics d'activité.")
        return

    top_day = daily_total.idxmax()
    top_day_likes = daily_likes.get(top_day, 0)
    top_day_comments = daily_comments.get(top_day, 0)
    top_day_total = daily_total.get(top_day, 0)

    weekly_likes = reactions.groupby(reactions["Date"].dt.to_period("W")).size()
    weekly_comments = comments.groupby(comments["Date"].dt.to_period("W")).size()
    weekly_total = weekly_likes.add(weekly_comments, fill_value=0)

    if not weekly_total.empty:
        top_week = weekly_total.idxmax()
        top_week_likes = weekly_likes.get(top_week, 0)
        top_week_comments = weekly_comments.get(top_week, 0)
        top_week_total = weekly_total.get(top_week, 0)
        top_week_date = format_date(top_week.start_time)
    else:
        top_week_date = "-"
        top_week_likes = top_week_comments = top_week_total = 0

    monthly_likes = reactions.groupby(reactions["Date"].dt.to_period("M")).size()
    monthly_comments = comments.groupby(comments["Date"].dt.to_period("M")).size()
    monthly_total = monthly_likes.add(monthly_comments, fill_value=0)

    if not monthly_total.empty:
        top_month = monthly_total.idxmax()
        top_month_likes = monthly_likes.get(top_month, 0)
        top_month_comments = monthly_comments.get(top_month, 0)
        top_month_total = monthly_total.get(top_month, 0)
        top_month_date = format_date(top_month.start_time)
    else:
        top_month_date = "-"
        top_month_likes = top_month_comments = top_month_total = 0

    plt.figure(figsize=(10, 4))
    plt.title("Pics d'activité LinkedIn")

    data = [
        ["Jour le plus actif", format_date(pd.to_datetime(top_day)), top_day_likes, top_day_comments, top_day_total],
        ["Semaine la plus active", top_week_date, top_week_likes, top_week_comments, top_week_total],
        ["Mois le plus actif", top_month_date, top_month_likes, top_month_comments, top_month_total],
    ]

    table = plt.table(
        cellText=data,
        colLabels=["Période", "Date", "Likes", "Commentaires", "Total"],
        cellLoc="center",
        loc="center"
    )

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()
    show_activity_peaks_comment(monthly_total)

    # Messages selon le niveau
def show_activity_peaks_comment(monthly_total):
    """
    Affiche un message en précisant le mois du pic d'activité.
    """

    if monthly_total is None or monthly_total.empty:
        messagebox.showinfo("Pics d'activité", "⚠️ Aucune donnée disponible pour détecter un pic d’activité.")
        return

    # monthly_total est une Series → on l'utilise directement
    monthly_totals = monthly_total

    # Convertir PeriodIndex → Timestamp
    if isinstance(monthly_totals.index[0], pd.Period):
        monthly_totals.index = monthly_totals.index.to_timestamp()

    # Mois du pic
    peak_month = monthly_totals.idxmax()
    peak_month_str = peak_month.strftime("%B %Y")

    peak_value = monthly_totals.max()

    # Messages selon le niveau
    import random
    if peak_value >= 40:
        messages = [
            f"Wow, incroyable ! {peak_month_str} a été votre mois le plus actif. Une superbe dynamique !",
            f"Performance exceptionnelle en {peak_month_str}. Vous étiez au top de votre engagement !",
            f"Activité impressionnante en {peak_month_str}. Vous avez vraiment brillé !"
        ]

    elif peak_value >= 15:
        messages = [
            f"Beau mois d’activité en {peak_month_str}. Continuez sur cette lancée !",
            f"Joli rythme en {peak_month_str}. Vous êtes sur la bonne voie !",
            f"Belle énergie en {peak_month_str}. Encore un petit effort et vous atteindrez un nouveau sommet !"
        ]

    else:
        messages = [
            f"{peak_month_str} a été votre mois le plus actif, mais votre rythme reste calme. Vous pouvez facilement augmenter votre présence.",
            f"Une petite activité en {peak_month_str}. Chaque interaction compte, vous êtes sur la bonne voie.",
            f"{peak_month_str} montre un début d’engagement. Rien ne presse, vous pouvez progresser à votre rythme."
        ]

    message = random.choice(messages)
    messagebox.showinfo("Pics d'activité", message)
    
# ---------------------------------------------------------
# Analyses : régularité des interactions
# ---------------------------------------------------------

def analyze_interaction_intervals(df_all):
    df_sorted = df_all.sort_values("Date")
    df_sorted["interval"] = df_sorted["Date"].diff()
    intervals = df_sorted["interval"].dropna()

    return (
        intervals,
        intervals.mean(),
        intervals.median(),
        intervals.max(),
        intervals.min()
    )


def show_intervals_page(df_all):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour analyser les intervalles.")
        return

    intervals, mean_interval, median_interval, max_interval, min_interval = analyze_interaction_intervals(df_all)
    
    df = df_all.copy()
    df["count"] = 1

    monthly_total = df.groupby(df["Date"].dt.to_period("M"))["count"].sum()


    plt.figure(figsize=(10, 4))
    plt.title("Régularité des interactions LinkedIn")

    data = [
        ["Temps moyen entre interactions", str(mean_interval)],
        ["Temps médian", str(median_interval)],
        ["Plus longue période sans interaction", str(max_interval)],
        ["Plus courte période (hyper-activité)", str(min_interval)],
    ]

    table = plt.table(
        cellText=data,
        colLabels=["Indicateur", "Durée"],
        cellLoc="center",
        loc="center"
    )

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

# ---------------------------------------------------------
# Analyses : périodes extrêmes
# ---------------------------------------------------------

def find_extreme_periods(df_all):
    df_sorted = df_all.sort_values("Date")
    df_sorted["interval"] = df_sorted["Date"].diff()
    df_sorted = df_sorted.dropna(subset=["interval"])

    max_interval = df_sorted["interval"].max()
    max_row = df_sorted.loc[df_sorted["interval"].idxmax()]
    max_end = max_row["Date"]
    max_start = max_end - max_interval

    min_interval = df_sorted["interval"].min()
    min_row = df_sorted.loc[df_sorted["interval"].idxmin()]
    min_end = min_row["Date"]
    min_start = min_end - min_interval

    return {
        "max_interval": max_interval,
        "max_start": max_start,
        "max_end": max_end,
        "min_interval": min_interval,
        "min_start": min_start,
        "min_end": min_end
    }


def show_extreme_periods_page(df_all):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour analyser les périodes extrêmes.")
        return

    periods = find_extreme_periods(df_all)
    
    df = df_all.copy()
    df["count"] = 1

    monthly_total = df.groupby(df["Date"].dt.to_period("M"))["count"].sum()

    plt.figure(figsize=(10, 4))
    plt.title("Périodes extrêmes d'activité")

    data = [
        ["Plus longue période sans activité",
         f"{format_date(periods['max_start'])} → {format_date(periods['max_end'])}",
         str(periods["max_interval"])],

        ["Période d'hyper-activité",
         f"{format_datetime(periods['min_start'])} → {format_datetime(periods['min_end'])}",
         str(periods["min_interval"])]
    ]

    table = plt.table(
        cellText=data,
        colLabels=["Type", "Dates", "Durée"],
        cellLoc="center",
        loc="center"
    )

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

    show_extreme_periods_comment(monthly_total)


def show_extreme_periods_comment(monthly_total):
    """
    Message global basé sur la période la plus active et la période la plus calme.
    """

    if monthly_total is None or monthly_total.empty:
        messagebox.showinfo("Analyse des périodes", "Aucune donnée disponible pour analyser les périodes extrêmes.")
        return

    # Convertir PeriodIndex → Timestamp si nécessaire
    if isinstance(monthly_total.index[0], pd.Period):
        monthly_total.index = monthly_total.index.to_timestamp()

    # Mois le plus actif et le plus calme
    peak_month = monthly_total.idxmax()
    low_month = monthly_total.idxmin()

    peak_month_str = peak_month.strftime("%B %Y")
    low_month_str = low_month.strftime("%B %Y")

    # Niveau d'activité
    peak_value = monthly_total.max()

    # Message automatique
    if peak_value >= 40:
        message = (
            f"Votre période la plus active se situe en {peak_month_str}, "
            f"tandis que la période la plus calme apparaît en {low_month_str}. "
            f"Votre activité montre une dynamique particulièrement soutenue."
        )

    elif peak_value >= 15:
        message = (
            f"Votre période la plus active se situe en {peak_month_str}, "
            f"et la plus calme en {low_month_str}. "
            f"Votre rythme est équilibré, avec des variations naturelles."
        )

    else:
        message = (
            f"Votre période la plus active se situe en {peak_month_str}, "
            f"et la plus calme en {low_month_str}. "
            f"Votre activité reste modérée, mais elle évolue de manière régulière."
        )

    messagebox.showinfo("Analyse des périodes extrêmes", message)
    
# ---------------------------------------------------------
# Analyses : moments de la journée
# ---------------------------------------------------------

def period_of_day(hour):
    if 5 <= hour < 12:
        return "Matin"
    elif 12 <= hour < 17:
        return "Après-midi"
    elif 17 <= hour < 22:
        return "Soir"
    else:
        return "Nuit"


def analyze_time_of_day(df_all):
    df = df_all.copy()
    df["moment"] = df["hour"].apply(period_of_day)
    return df["moment"].value_counts()


def show_time_of_day_page(df_all):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour analyser le moment de la journée.")
        return

    counts = analyze_time_of_day(df_all)

    plt.figure(figsize=(8, 5))
    plt.title("Activité selon le moment de la journée")

    labels = counts.index
    values = counts.values

    plt.bar(labels, values, color=["#FFDD57", "#FFAA00", "#FF6F00", "#003366"])
    plt.xlabel("Moment de la journée")
    plt.ylabel("Nombre d'interactions")
    plt.tight_layout()
    plt.show()
    
# ---------------------------------------------------------
# Heatmap jour × tranche horaire
# ---------------------------------------------------------

def analyze_heatmap(df_all):
    df = df_all.copy()
    df["moment"] = df["hour"].apply(period_of_day)

    order_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

    pivot = df.pivot_table(
        index="moment",
        columns="weekday",
        values="Date",
        aggfunc="count",
        fill_value=0
    )

    pivot = pivot.reindex(index=["Matin", "Après-midi", "Soir", "Nuit"])
    pivot = pivot.reindex(columns=order_days)

    return pivot

def show_heatmap_comment(pivot):
    """
    Analyse la heatmap pour déterminer le jour et la tranche horaire les plus actifs.
    """

    if pivot is None or pivot.empty:
        messagebox.showinfo("Analyse Heatmap", "Aucune donnée disponible pour analyser les périodes d'activité.")
        return

    # Total par jour
    day_totals = pivot.sum(axis=0)
    best_day = day_totals.idxmax()

    # Total par tranche horaire
    moment_totals = pivot.sum(axis=1)
    best_moment = moment_totals.idxmax()

    # Message final
    message = (
        f"Votre activité est la plus élevée le {best_day}, "
        f"et elle atteint son maximum durant la tranche horaire « {best_moment} ». "
        f"Ces moments représentent vos périodes d'engagement les plus marquées."
    )

    messagebox.showinfo("Analyse Heatmap", message)
    
def show_heatmap_page(df_all):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour la heatmap.")
        return

    pivot = analyze_heatmap(df_all)

    plt.figure(figsize=(10, 6))
    plt.title("Heatmap : Activité par jour × tranche horaire")

    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        annot=True,
        fmt="d",
        linewidths=.5,
        cbar=True
    )

    plt.xlabel("Jour de la semaine")
    plt.ylabel("Tranche horaire")
    plt.tight_layout()
    plt.show()

    show_heatmap_comment(pivot)

# ---------------------------------------------------------
# Analyse de saisonnalité
# ---------------------------------------------------------

def analyze_seasonality(df_all):
    df = df_all.copy()
    monthly_counts = df.groupby("month").size()

    month_names = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    # Réindexer pour avoir les 12 mois même si certains sont vides
    monthly_counts = monthly_counts.reindex(range(1, 13), fill_value=0)
    monthly_counts.index = month_names

    return monthly_counts


def show_seasonality_page(df_all):
    if df_all is None or df_all.empty:
        messagebox.showwarning("Données manquantes", "Aucune interaction disponible pour l'analyse de saisonnalité.")
        return

    monthly_counts = analyze_seasonality(df_all)

    colors = [
        "#4A90E2", "#6BB9F0", "#89CFF0",
        "#2ECC71", "#27AE60", "#1E8449",
        "#F1C40F", "#F39C12", "#E67E22",
        "#D35400", "#C0392B", "#922B21"
    ]

    plt.figure(figsize=(12, 6))
    plt.title("Analyse de saisonnalité : Activité par mois")

    sns.barplot(x=monthly_counts.index, y=monthly_counts.values, palette=colors)

    plt.xticks(rotation=45)
    plt.ylabel("Nombre d'interactions")
    plt.tight_layout()
    plt.show()

# ---------------------------------------------------------
# Analyse : emplois sauvegardés
# ---------------------------------------------------------

def prepare_saved_jobs(df_saved):
    """
    Prépare les données des offres sauvegardées :
    - vérifie la colonne 'Saved Date'
    - conversion des dates
    - tri chronologique
    - agrégation par mois
    """
    if df_saved is None or df_saved.empty:
        return None, None

    df = df_saved.copy()
    df.columns = df.columns.str.strip()  # Nettoyage des noms de colonnes

    # Vérification de la colonne de date
    if "Saved Date" not in df.columns:
        messagebox.showerror("Erreur", "La colonne 'Saved Date' est introuvable dans Saved Jobs.csv.")
        return None, None

    # Conversion des dates
    df["Saved Date"] = pd.to_datetime(df["Saved Date"], errors="coerce")
    df = df.dropna(subset=["Saved Date"])

    # Extraction année-mois
    df["year_month"] = df["Saved Date"].dt.to_period("M")
    df = df.sort_values("Saved Date")

    # Comptage par mois
    monthly_counts = df.groupby("year_month").size()
    monthly_counts.index = monthly_counts.index.to_timestamp()

    return df, monthly_counts


def show_saved_jobs_comment(df, monthly_counts):
    """
    Message professionnel et synthétique sur les tendances des offres sauvegardées.
    """

    if df is None or df.empty or monthly_counts is None or monthly_counts.empty:
        messagebox.showinfo("Analyse des offres sauvegardées",
                            "Aucune donnée exploitable pour générer un commentaire.")
        return

    # Mois le plus actif
    peak_month = monthly_counts.idxmax()
    peak_month_str = peak_month.strftime("%B %Y")

    # Entreprise la plus ciblée
    top_company = df["Company Name"].value_counts().idxmax()

    # Intitulé le plus fréquent
    top_title = df["Job Title"].value_counts().idxmax()

    # Message final
    message = (
        f"Votre activité de sauvegarde d'offres est particulièrement marquée en {peak_month_str}. "
        f"Vous semblez accorder une attention particulière aux opportunités proposées par {top_company}, "
        f"et les postes de type « {top_title} » reviennent régulièrement dans vos sélections. "
        f"Ces éléments dessinent une orientation claire dans votre recherche et confirment la cohérence de vos objectifs professionnels."
    )

    messagebox.showinfo("Analyse des offres sauvegardées", message)


def show_saved_jobs_analysis(df_saved):
    """
    Affiche :
    - graphique de sauvegarde par mois
    - entreprises les plus ciblées
    - intitulés les plus fréquents
    - indicateurs clés
    """
    if df_saved is None or df_saved.empty:
        messagebox.showwarning("Données manquantes", "Aucune donnée dans Saved Jobs.csv.")
        return

    df, monthly_counts = prepare_saved_jobs(df_saved)

    if df is None or monthly_counts is None or df.empty:
        messagebox.showwarning("Erreur", "Impossible d'analyser Saved Jobs.csv.")
        return

    # -----------------------------------------------------
    # 1) GRAPHIQUE DE SAUVEGARDE PAR MOIS
    # -----------------------------------------------------
    plt.figure(figsize=(12, 6))
    plt.title("Offres d'emploi sauvegardées par mois")

    plt.plot(monthly_counts.index, monthly_counts.values, marker="o", color="#27AE60")
    plt.fill_between(monthly_counts.index, monthly_counts.values, color="#ABEBC6", alpha=0.5)

    plt.xlabel("Mois")
    plt.ylabel("Nombre d'offres sauvegardées")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------
    # 2) ENTREPRISES LES PLUS CIBLÉES
    # -----------------------------------------------------
    top_companies = df["Company Name"].value_counts().head(5)

    plt.figure(figsize=(8, 4))
    plt.title("Entreprises les plus ciblées")

    sns.barplot(x=top_companies.values, y=top_companies.index, palette="Greens_r")
    plt.xlabel("Nombre d'offres sauvegardées")
    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------
    # 3) INTITULÉS LES PLUS FRÉQUENTS
    # -----------------------------------------------------
    top_titles = df["Job Title"].value_counts().head(5)

    plt.figure(figsize=(8, 4))
    plt.title("Intitulés de poste les plus fréquents")

    sns.barplot(x=top_titles.values, y=top_titles.index, palette="Blues_r")
    plt.xlabel("Fréquence")
    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------
    # 4) INDICATEURS CLÉS
    # -----------------------------------------------------
    total = len(df)
    most_active_month = monthly_counts.idxmax()
    most_active_value = monthly_counts.max()
    top_company = df["Company Name"].value_counts().idxmax()
    top_title = df["Job Title"].value_counts().idxmax()

    # MESSAGE AUTOMATIQUE AVANT LE TABLEAU
    show_saved_jobs_comment(df, monthly_counts)

    # -----------------------------------------------------
    # TABLEAU DES INDICATEURS
    # -----------------------------------------------------
    plt.figure(figsize=(10, 4))
    plt.title("Indicateurs clés de la recherche d'emploi")

    indicators = [
        ["Nombre total d'offres sauvegardées", total],
        ["Mois le plus actif", f"{format_date(most_active_month)} ({most_active_value} offres)"],
        ["Entreprise la plus ciblée", top_company],
        ["Intitulé le plus fréquent", top_title]
    ]

    table = plt.table(
        cellText=indicators,
        colLabels=["Indicateur", "Valeur"],
        cellLoc="center",
        loc="center"
    )

    for key, cell in table.get_celld().items():
        cell.set_fontsize(12)

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

# ---------------------------------------------------------
# PROFESSIONAL JOURNEY (Positions.csv)
# ---------------------------------------------------------
def prepare_positions(df_positions):
    if df_positions is None or df_positions.empty:
        return None

    df = df_positions.copy()
    df.columns = df.columns.str.strip()

    required = ["Started On", "Finished On", "Title", "Company Name"]
    for col in required:
        if col not in df.columns:
            messagebox.showerror("Erreur", f"La colonne '{col}' est manquante dans Positions.csv.")
            return None

    df["Started On"] = pd.to_datetime(df["Started On"], errors="coerce")
    df["Finished On"] = pd.to_datetime(df["Finished On"], errors="coerce")

    today = pd.Timestamp.today()
    df["Finished On"] = df["Finished On"].fillna(today)

    # Supprimer les lignes invalides
    df = df.dropna(subset=["Started On"])

    # Durée en mois
    df["Duration"] = (df["Finished On"] - df["Started On"]).dt.days / 30.44

    df = df.sort_values("Started On")

    return df


def show_professional_journey_page(df_positions):
    if df_positions is None or df_positions.empty:
        messagebox.showwarning("Données manquantes", "Aucune donnée dans Positions.csv.")
        return

    df = prepare_positions(df_positions)
    if df is None or df.empty:
        return

    # ---------------- TIMELINE ----------------
    plt.figure(figsize=(12, 6))
    plt.title("Timeline du parcours professionnel")

    y_positions = range(len(df))
    colors = sns.color_palette("husl", len(df))

    for i, (_, row) in enumerate(df.iterrows()):
        duration_days = (row["Finished On"] - row["Started On"]).days
        if duration_days <= 0:
            continue  # éviter les erreurs

        plt.barh(
            y=i,
            width=duration_days,
            left=row["Started On"],
            color=colors[i],
            alpha=0.8
        )

        plt.text(
            row["Started On"],
            i,
            f"{row['Title']} – {row['Company Name']}",
            va="center",
            ha="left",
            fontsize=9
        )

    plt.yticks(y_positions, [f"Exp {i+1}" for i in y_positions])
    plt.xlabel("Dates")
    plt.tight_layout()
    plt.show()

    # ---------------- INDICATEURS ----------------
    avg_duration = df["Duration"].mean()
    max_duration = df["Duration"].max()
    min_duration = df["Duration"].min()

    longest = df.loc[df["Duration"].idxmax()]
    shortest = df.loc[df["Duration"].idxmin()]

    plt.figure(figsize=(10, 4))
    plt.title("Indicateurs clés du parcours professionnel")

    indicators = [
        ["Durée moyenne d'un poste", f"{avg_duration:.1f} mois"],
        ["Plus longue expérience", f"{longest['Title']} – {longest['Company Name']} ({max_duration:.1f} mois)"],
        ["Plus courte expérience", f"{shortest['Title']} – {shortest['Company Name']} ({min_duration:.1f} mois)"],
        ["Nombre total d'expériences", len(df)]
    ]

    table = plt.table(
        cellText=indicators,
        colLabels=["Indicateur", "Valeur"],
        cellLoc="center",
        loc="center"
    )

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

# ---------------------------------------------------------
# ANALYSE DES SECTEURS (Connections.csv)
# ---------------------------------------------------------

def compute_sector_percentages(df):
    """
    Calcule les pourcentages de chaque secteur à partir de la colonne 'Sector'.
    """
    if df is None or df.empty:
        print("❌ Le DataFrame est vide.")
        return None

    if "Sector" not in df.columns:
        print("❌ La colonne 'Sector' est absente.")
        print("Colonnes disponibles :", df.columns.tolist())
        return None

    # Nettoyage
    df["Sector"] = df["Sector"].astype(str).str.strip()
    counts = df["Sector"].value_counts()
    percentages = (counts / counts.sum()) * 100

    return percentages.sort_values(ascending=False)


def plot_sector_bar_chart(df):
    """
    Affiche un graphique en barres des pourcentages par secteur.
    """
    percentages = compute_sector_percentages(df)
    if percentages is None or percentages.empty:
        print("❌ Aucun secteur à afficher.")
        return

    plt.figure(figsize=(10, 5))
    sns.barplot(
        x=percentages.values,
        y=percentages.index,
        palette="viridis"
    )
    plt.title("Répartition des secteurs dans les connexions")
    plt.xlabel("Pourcentage (%)")
    plt.ylabel("Secteur")
    plt.tight_layout()
    plt.show()

    # Message automatique
    show_sector_comment(df)


def show_sector_table(df):
    """
    Affiche un tableau des pourcentages par secteur.
    """
    percentages = compute_sector_percentages(df)

    if percentages is None or percentages.empty:
        messagebox.showinfo("Analyse des secteurs", "Aucun secteur exploitable pour afficher le tableau.")
        return

    table_data = [
        [sector, f"{pct:.1f}%"]
        for sector, pct in percentages.items()
    ]

    plt.figure(figsize=(8, 0.5 + len(table_data) * 0.4))
    plt.title("Tableau des pourcentages par secteur")

    ax = plt.gca()
    ax.axis("off")

    table = plt.table(
        cellText=table_data,
        colLabels=["Secteur", "Pourcentage"],
        cellLoc="center",
        loc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.4)

    plt.tight_layout()
    plt.show()


def show_sector_comment(df):
    """
    Message professionnel et sympathique indiquant le secteur dominant.
    """

    percentages = compute_sector_percentages(df)

    if percentages is None or percentages.empty:
        messagebox.showinfo("Analyse des secteurs", "Aucun secteur exploitable pour générer un commentaire.")
        return

    # Secteur dominant
    top_sector = percentages.index[0]

    # Message professionnel et sympa
    message = (
        f"Votre réseau montre une affinité particulière avec le secteur « {top_sector} ». "
        f"C’est clairement un domaine qui retient davantage votre attention et reflète vos centres d’intérêt actuels."
    )

    messagebox.showinfo("Analyse des secteurs", message)

# ---------------------------------------------------------
# NETWORK GROWTH (Connections.csv)
# ---------------------------------------------------------

def prepare_connections(df_connections):
    """
    Prépare les données de croissance du réseau :
    - conversion des dates
    - agrégation par mois
    """
    if df_connections is None or df_connections.empty:
        return None, None

    df = df_connections.copy()
    df["Connected On"] = pd.to_datetime(df["Connected On"], errors="coerce")
    df = df.dropna(subset=["Connected On"])
    df["year_month"] = df["Connected On"].dt.to_period("M")
    df = df.sort_values("Connected On")

    monthly_counts = df.groupby("year_month").size()
    monthly_counts.index = monthly_counts.index.to_timestamp()

    return df, monthly_counts


def show_network_growth_page(df_connections):
    """
    Affiche :
    - graphique de croissance du réseau
    - indicateurs clés
    - message narratif sur la meilleure période
    """
    if df_connections is None or df_connections.empty:
        messagebox.showwarning("Données manquantes", "Aucune donnée dans Connections.csv.")
        return

    df, monthly_counts = prepare_connections(df_connections)

    # -----------------------------------------------------
    # 1) GRAPHIQUE DE CROISSANCE
    # -----------------------------------------------------
    plt.figure(figsize=(12, 6))
    plt.title("Croissance du réseau LinkedIn")

    plt.plot(monthly_counts.index, monthly_counts.values, marker="o", color="#2E86C1")
    plt.fill_between(monthly_counts.index, monthly_counts.values, color="#AED6F1", alpha=0.5)

    plt.xlabel("Mois")
    plt.ylabel("Connexions")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------
    # 2) INDICATEURS CLÉS
    # -----------------------------------------------------
    total = len(df)
    most_active_month = monthly_counts.idxmax()
    most_active_value = monthly_counts.max()
    least_active_month = monthly_counts.idxmin()
    least_active_value = monthly_counts.min()
    avg_growth = monthly_counts.mean()

    plt.figure(figsize=(12, 6))
    plt.title("Indicateurs clés de la croissance du réseau")

    indicators = [
        ["Nombre total de connexions", total],
        ["Mois le plus actif", f"{format_date(most_active_month)} ({most_active_value} connexions)"],
        ["Mois le plus calme", f"{format_date(least_active_month)} ({least_active_value} connexions)"],
        ["Croissance moyenne mensuelle", f"{avg_growth:.1f} connexions/mois"]
    ]

    table = plt.table(
        cellText=indicators,
        colLabels=["Indicateur", "Valeur"],
        cellLoc="center",
        loc="center"
    )

    for key, cell in table.get_celld().items():
        cell.set_fontsize(12)

    table.scale(1, 2)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------
    # 3) MESSAGE : REPRENDRE LE RYTHME DE LA MEILLEURE PÉRIODE
    # -----------------------------------------------------
    best_period = most_active_month
    best_period_str = format_date(best_period)

    message = (
        f"Votre réseau a connu son élan le plus fort en {best_period_str}. "
        f"Reprendre le rythme de cette période pourrait renforcer encore davantage votre dynamique professionnelle."
    )

    messagebox.showinfo("Croissance du réseau", message)

# ---------------------------------------------------------
# Interface interactive (Tkinter) + Consentement RGPD
# ---------------------------------------------------------
def ask_user_consent():
    """
    Fenêtre RGPD : demande à l'utilisateur s'il accepte l'utilisation
    de ses données. Retourne True si accepté, False sinon.
    """
    consent_window = tk.Toplevel()
    consent_window.title("Consentement RGPD")
    consent_window.geometry("480x260")
    consent_window.grab_set()

    message = (
        "Ce programme analyse vos données exportées depuis LinkedIn.\n\n"
        "Conformément au RGPD :\n"
        "- Vos données restent strictement locales sur votre ordinateur.\n"
        "- Elles ne sont jamais envoyées, partagées ou stockées ailleurs.\n"
        "- Vous pouvez refuser l'analyse à tout moment.\n\n"
        "Acceptez-vous l'utilisation de vos données pour lancer l'analyse ?"
    )

    label = ttk.Label(consent_window, text=message, wraplength=450, justify="left")
    label.pack(pady=15)

    user_choice = {"accepted": False}

    def accept():
        user_choice["accepted"] = True
        consent_window.destroy()

    def refuse():
        user_choice["accepted"] = False
        consent_window.destroy()

    btn_frame = ttk.Frame(consent_window)
    btn_frame.pack(pady=10)

    ttk.Button(btn_frame, text="J'accepte", command=accept).pack(side="left", padx=10)
    ttk.Button(btn_frame, text="Je refuse", command=refuse).pack(side="left", padx=10)

    consent_window.wait_window()
    return user_choice["accepted"]

def launch_interface(initial_state, data_dir):

    state = initial_state.copy()

    def update_files_label():
        info = state["files_info"]
        lines = ["Fichiers détectés :"]
        for name, present in info.items():
            symbol = "✔" if present else "✖"
            lines.append(f"{symbol} {name}.csv")
        files_label.config(text="\n".join(lines))

    def refresh_data():
        new_state = detect_and_load_data(data_dir)
        state.update(new_state)
        update_files_label()
        print("Données actualisées.")

    def run_analysis():
        all_selected = var_all.get()

        if all_selected or var_monthly.get():
            print("✅ Analyse : évolution mensuelle")
            plot_monthly_activity(state["activity_counts"], state["events"])

        if all_selected or var_cumulative.get():
            print("✅ Analyse : évolution cumulée")
            plot_cumulative_activity(state["df_all"], state["events"])
            
        if all_selected or var_peaks.get():
            print("✅ Analyse : pics d'activité")
            show_activity_peaks_page(state["reactions"], state["comments"])

        if all_selected or var_intervals.get():
            print("✅ Analyse : régularité des interactions")
            show_intervals_page(state["df_all"])

        if all_selected or var_extremes.get():
            print("✅ Analyse : périodes extrêmes")
            show_extreme_periods_page(state["df_all"])

        if all_selected or var_timeofday.get():
            print("✅ Analyse : activité selon le moment de la journée")
            show_time_of_day_page(state["df_all"])

        if all_selected or var_heatmap.get():
            print("✅ Analyse : heatmap jour × tranche horaire")
            show_heatmap_page(state["df_all"])

        if all_selected or var_seasonality.get():
            print("✅ Analyse : saisonnalité")
            show_seasonality_page(state["df_all"])

        if all_selected or var_jobsaved.get():
            print("✅ Analyse : offres sauvegardées")
            show_saved_jobs_analysis(state["saved_jobs"])

        if all_selected or var_journey.get():
            print("✅ Analyse : parcours professionnel")
            show_professional_journey_page(state["positions"])

        if all_selected or var_sector.get():
            print("✅ Analyse : secteurs des connexions")
            plot_sector_bar_chart(state["connections"])
            show_sector_table(state["connections"])

        if all_selected or var_network.get():
            print("✅ Analyse : croissance du réseau")
            show_network_growth_page(state["connections"])

    def on_launch_analysis():
        if not ask_user_consent():
            messagebox.showinfo("Analyse annulée", "Vous avez refusé l'utilisation des données.")
            return
        run_analysis()

    root = tk.Tk()
    root.title("Analyse LinkedIn – Choix des visualisations")

    ttk.Label(root, text="Sélectionne ce que tu veux analyser :", font=("Arial", 12)).pack(pady=10)

    ttk.Button(root, text="Actualiser les données", command=refresh_data).pack(pady=(0, 10))

    files_label = ttk.Label(root, text="", justify="left", font=("Arial", 9))
    files_label.pack(padx=20, pady=(0, 10), anchor="w")

    var_all = tk.BooleanVar()
    var_monthly = tk.BooleanVar()
    var_cumulative = tk.BooleanVar()
    var_peaks = tk.BooleanVar()
    var_intervals = tk.BooleanVar()
    var_extremes = tk.BooleanVar()
    var_timeofday = tk.BooleanVar()
    var_heatmap = tk.BooleanVar()
    var_seasonality = tk.BooleanVar()
    var_journey = tk.BooleanVar()
    var_network = tk.BooleanVar()
    var_jobsaved = tk.BooleanVar()
    var_sector = tk.BooleanVar()

    ttk.Checkbutton(root, text="Tout analyser", variable=var_all).pack(anchor="w", padx=20, pady=(0, 10))

    ttk.Checkbutton(root, text="Évolution mensuelle", variable=var_monthly).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Évolution cumulée", variable=var_cumulative).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Pics d'activité", variable=var_peaks).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Régularité des interactions", variable=var_intervals).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Périodes extrêmes (absence / hyper-activité)", variable=var_extremes).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Activité selon le moment de la journée", variable=var_timeofday).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Heatmap jour × tranche horaire", variable=var_heatmap).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Analyse de saisonnalité (activité par mois)", variable=var_seasonality).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Analyse des offres sauvegardées", variable=var_jobsaved).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Analyse du parcours professionnel", variable=var_journey).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Analyse des secteurs des connexions", variable=var_sector).pack(anchor="w", padx=20)
    ttk.Checkbutton(root, text="Analyse de la croissance du réseau", variable=var_network).pack(anchor="w", padx=20)

    ttk.Button(root, text="Lancer l'analyse", command=on_launch_analysis).pack(pady=20)

    update_files_label()
    root.mainloop()

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

def main():
    if not os.path.isdir(DATA_DIR):
        print(f"Le dossier de données n'existe pas : {DATA_DIR}")
        return

    initial_state = detect_and_load_data(DATA_DIR)
    launch_interface(initial_state, DATA_DIR)

if __name__ == "__main__":
    main()