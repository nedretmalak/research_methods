import pandas as pd
import glob
import os
import re

#Load all Excel files from the specified directory
files = glob.glob("/Users/nedret/Desktop/cw2_data/*.xls*")
all_data = []


def extract_years(filename):
    """
    Extract start and end years from the filename using multiple regex patterns.
    Handles both 2-digit and 4-digit year formats.
    """

    patterns = [
        r'sum-(\d{2})-(\d{2})',
        r'sum-(\d{4})-(\d{2})',
        r'(\d{4})-(\d{2}).*sum',
        r'(\d{2})-(\d{2}).*sum',
        r'prim-diag-(\d{2})-(\d{2})',
        r'prim-(\d{4})-(\d{2})-diag-sum',
        r'diag-(\d{4})-(\d{2})-prim-diag-sum',
    ]

    #Try each pattern until a match is found
    for pattern in patterns:
        m = re.search(pattern, filename)
        if m:
            a, b = m.group(1), m.group(2)

            #Convert start year
            if len(a) == 4:
                start_year = int(a)
            else:
                a = int(a)
                start_year = 1900 + a if a >= 98 else 2000 + a

            #Convert end year
            b = int(b)
            end_year = 1900 + b if b >= 98 else 2000 + b

            return start_year, end_year

    #Return None if no valid pattern is found
    return None, None


def clean_col_name(col):
    """
    Clean column names by:
    - Converting to string
    - Removing line breaks
    - Normalising whitespace
    """

    col = str(col)
    col = col.replace("\n", " ")
    col = col.replace("\r", " ")
    col = re.sub(r"\s+", " ", col).strip()
    return col


def find_header_row(raw_df, max_rows=20):
    """
    Detect the header row by searching for known keywords
    within the first few rows of the raw dataframe.
    """

    keywords = [
        "primary diagnosis",
        "diagnosis summary",
        "primary diagnosis - summary",
        "primary diagnosis summary",
    ]

    #Scan first 'max_rows' rows for header indicators
    for i in range(min(max_rows, len(raw_df))):
        row_values = raw_df.iloc[i].astype(str).apply(clean_col_name).str.lower().tolist()
        row_text = " | ".join(row_values)

        if any(k in row_text for k in keywords):
            return i

    return None


def load_file(file):
    """
    Load a single Excel file and:
    - Detect header row dynamically
    - Clean column names
    - Remove empty columns
    """

    try:
        raw = pd.read_excel(file, header=None)
    except Exception as e:
        print(f"Failed to read file: {os.path.basename(file)} -> {e}")
        return None, None

    header_row = find_header_row(raw)

    #If header cannot be detected, skip file
    if header_row is None:
        return None, None

    #Extract data below header
    df = raw.iloc[header_row + 1:].copy()

    #Assign cleaned column names
    df.columns = [clean_col_name(c) for c in raw.iloc[header_row].tolist()]

    #Drop completely empty columns
    df = df.dropna(axis=1, how='all')

    return df, header_row


def find_category_column(columns):
    """
    Identify the column that represents diagnosis categories.
    """

    for c in columns:
        cl = clean_col_name(c).lower()

        #Prefer more specific match first
        if "diagnosis" in cl and "summary" in cl:
            return c

        #Fallback option
        if "primary diagnosis" in cl:
            return c

    return None


#Process each file individually
for file in files:
    filename = os.path.basename(file)

    #Extract year range from filename
    start_year, end_year = extract_years(filename)
    if start_year is None or end_year is None:
        print(f"Year information not found, skipping file: {filename}")
        continue

    #Load dataset and detect header
    df, header_row = load_file(file)
    if df is None:
        print(f"Header row not detected, skipping file: {filename}")
        continue

    #Standardise column names
    df.columns = [clean_col_name(c) for c in df.columns]

    #Identify category column
    category_col = find_category_column(df.columns)
    if category_col is None:
        print(f"Category column not found: {filename}")
        print("Detected columns:", df.columns.tolist()[:12])
        continue

    #Mapping of desired final column names to possible variants
    desired_map = {
        'Admissions': [
            'Admissions',
            'Admission',
            'Finished Admissions',
            'Finished Admission Episodes',
            'Finished Admissions Episodes',
            'Finished Admissions Episode',
            'Admissions ',
            'Finished Admissions '
        ],
        'Male': ['Male'],
        'Emergency': ['Emergency'],
        'Waiting List': ['Waiting List'],
        'Mean Waiting Time': ['Mean Waiting Time'],
        'Median Waiting Time': ['Median Waiting Time'],
        'Mean length of stay': ['Mean length of stay'],
        'Median length of stay': ['Median length of stay'],
        'Mean Age': ['Mean Age'],
        'Age 0-14': ['Age 0-14'],
        'Age 15-59': ['Age 15-59'],
        'Age 60-74': ['Age 60-74'],
        'Age 75+': ['Age 75+'],
        'Day case': ['Day case'],
        'Bed days': ['Bed days', 'Bed Days'],
    }

    #Initialise selected columns with category column
    selected = {category_col: 'Category'}

    #Match actual columns to desired schema
    for final_name, candidates in desired_map.items():
        found = False

        for real_col in df.columns:
            real_clean = clean_col_name(real_col).lower()

            for cand in candidates:
                cand_clean = clean_col_name(cand).lower()

                if real_clean == cand_clean:
                    selected[real_col] = final_name
                    found = True
                    break

            if found:
                break

        #Extra fallback logic specifically for Admissions column
        if final_name == 'Admissions' and not found:
            for real_col in df.columns:
                real_clean = clean_col_name(real_col).lower()

                if (
                    'admission' in real_clean
                    and 'mean' not in real_clean
                    and 'median' not in real_clean
                    and 'age' not in real_clean
                ):
                    selected[real_col] = 'Admissions'
                    found = True
                    print(f"Admissions fallback applied in {filename}: {real_col}")
                    break

    #Keep only selected columns
    existing_selected_keys = [k for k in selected.keys() if k in df.columns]
    df = df[existing_selected_keys].copy()

    #Rename columns to standard format
    df = df.rename(columns=selected)

    #Ensure required columns exist
    if 'Category' not in df.columns:
        print(f"Category column renaming failed: {filename}")
        continue

    if 'Admissions' not in df.columns:
        print(f"Admissions column not found: {filename}")
        print("Detected columns:", df.columns.tolist())
        continue

    #Clean category values
    df = df[df['Category'].notna()]
    df['Category'] = df['Category'].astype(str).str.strip()

    #Remove unnecessary or invalid rows
    df = df[df['Category'] != '']
    df = df[~df['Category'].str.lower().eq('total')]
    df = df[~df['Category'].str.lower().str.contains('copyright', na=False)]

    #Convert all numeric columns safely
    numeric_cols = [c for c in df.columns if c != 'Category']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    #Duplicate dataset for both years (start and end year)
    for y in [start_year, end_year]:
        temp = df.copy()
        temp["Year"] = y
        all_data.append(temp)

    print(f"Processed successfully: {filename} | header_row={header_row} | years={start_year}-{end_year}")


#Final aggregation step
if not all_data:
    print("No data could be loaded from the provided files.")
else:
    # Combine all processed data
    final_df = pd.concat(all_data, ignore_index=True)

    print("\n- FIRST 5 ROWS -")
    print(final_df.head())

    print("\n- COLUMN NAMES -")
    print(final_df.columns.tolist())

    print("\n- YEAR RANGE -")
    print(final_df["Year"].min(), final_df["Year"].max())

    print("\n- UNIQUE YEARS -")
    print(sorted(final_df["Year"].dropna().unique().tolist()))

    print("\n- DATASET SHAPE -")
    print(final_df.shape)

    #Evaluate completeness of Admissions data
    admissions_check = final_df.groupby("Year")["Admissions"].apply(lambda x: x.notna().sum())
    print("\n- NON-NULL ADMISSIONS COUNT (BY YEAR) -")
    print(admissions_check)

    #Save final cleaned dataset
    output_path = "/Users/nedret/Desktop/cw2_data/cleaned_hospital_admissions_v5.csv"
    final_df.to_csv(output_path, index=False)

    print(f"\nCleaned dataset saved to: {output_path}")
