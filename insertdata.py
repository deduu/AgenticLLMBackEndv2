import re
from sqlalchemy import create_engine, Column, Integer, String, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

# Define the Base and the EconomicSectorData model
Base = declarative_base()

class EconomicSectorData(Base):
    __tablename__ = 'economic_sector_data'
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    quarter = Column(String(2), nullable=False)
    sector = Column(String(255), nullable=False)
    country = Column(String(255), nullable=False)
    value = Column(Float, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('year', 'quarter', 'sector', 'country', name='uq_economic_sector'),
    )

# Database setup for SQLite
# You can specify a file path or use ':memory:' for an in-memory database
DATABASE_URL = "sqlite:///economic_sector_data.db"  # This will create a file named economic_sector_data.db
# DATABASE_URL = "sqlite:///:memory:"  # Use this for an in-memory database

engine = create_engine(DATABASE_URL, echo=False)  # Set echo=True for SQL logging
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

# Create tables
Base.metadata.create_all(bind=engine)

# Sample data as a multiline string (replace this with your actual data source)
data = """
Q4		Q1*	Q2*	Q3*	Q4*		Q1*	Q2*	Q3**			
1			Pendidikan	1	2	14	55	48	0	2	0	0	2	1	3	0	0	0		Education	1
2			Brunei Darussalam	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Brunei Darussalam	2
3			Kamboja	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Cambodia	3
4			Laos	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Lao PDR	4
5			Malaysia	0	0	0	-	-	-	-	0	0	0	0	0	0	0	0		Malaysia	5
6			Myanmar	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Myanmar	6
7			Filipina	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Philippines	7
8			Singapura	1	2	14	55	48	0	2	0	0	2	1	3	0	0	0		Singapore	8
9			Thailand	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Thailand	9
10			Vietnam	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Vietnam	10
11			Kesehatan dan Pekerjaan Sosial	54	76	48	4	496	42	82	230	44	26	-2	299	98	492	1.661		Health and Social Work	11
12			Brunei Darussalam	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Brunei Darussalam	12
13			Kamboja	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Cambodia	13
14			Laos	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Lao PDR	14
15			Malaysia	-	0	0	2	1	-	-2	-	-	-	-	-	0	-	0		Malaysia	15
16			Myanmar	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Myanmar	16
17			Filipina	-	-	-	-	-	-	-	-	-	0	0	-	0	0	-		Philippines	17
18			Singapura	24	22	25	13	455	35	63	247	23	26	24	320	2	471	1.644		Singapore	18
19			Thailand	31	54	23	-10	40	7	20	-17	21	0	-25	-22	96	22	17		Thailand	19
20			Vietnam	-	-	-	-	-	-	-	0	0	-	-	-	-	-	-		Vietnam	20
21			Jasa Kemasyarakatan, Sosial, dan Perseorangan Lainnya	62	29	22	3	0	0	2	34	1	0	0	35	0	1	0		Other Community, Social, and Personal Service Activities	21
22			Brunei Darussalam	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Brunei Darussalam	22
23			Kamboja	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Cambodia	23
24			Laos	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Lao PDR	24
25			Malaysia	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Malaysia	25
26			Myanmar	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Myanmar	26
27			Filipina	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Philippines	27
28			Singapura	62	29	21	2	0	0	2	34	1	0	0	35	0	1	0		Singapore	28
29			Thailand	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Thailand	29
30			Vietnam	-	-	1	1	-	-	-	-	-	-	-	-	-	-	-		Vietnam	30
31			Lainnya	475	-47	184	267	-213	-305	-475	93	49	87	111	339	77	-37	-87		Others	31
32			Brunei Darussalam	-	-	-	-	-	-	0	-	-	-	-	-	-	-	-		Brunei Darussalam	32
33			Kamboja	-	-	-	-	-	0	-	-	-	0	-	0	-	1	-1		Cambodia	33
34			Laos	-	-	-	-	-	-	-	-	-	-	-	-	-	-	-		Lao PDR	34
35			Malaysia	506	0	1	0	0	-	2	1	0	-6	4	-1	1	0	0		Malaysia	35
36			Myanmar	1	1	0	0	1	0	-1	0	0	0	0	0	0	0	0		Myanmar	36
37			Filipina	0	1	0	0	0	2	3	-2	0	1	0	-1	0	1	0		Philippines	37
38			Singapura	-32	-51	147	270	-215	-305	-464	97	49	90	109	344	76	-38	-87		Singapore	38
39			Thailand	0	1	35	-4	2	-2	-16	-3	-1	2	-2	-4	0	0	0		Thailand	39
40			Vietnam	0	-	2	0	0	0	1	0	0	0	0	1	0	0	0		Vietnam	40
41			Jumlah	10.190	11.157	6.880	7.928	7.404	1.319	10.747	1.298	1.965	656	2.376	6.295	2.841	3.046	4.212		Total	41
42			Brunei Darussalam	-3	-3	-3	0	0	0	1	0	0	0	0	0	0	0	0		Brunei Darussalam	42
43			Kamboja	0	1	0	2	1	2	3	1	0	1	0	2	0	1	-1		Cambodia	43
44			Laos	-	-	-	-	-	-	-	-	-	-	-	-	-	0	0		Lao PDR	44
45			Malaysia	976	621	-608	415	-26	574	995	6	13	18	432	469	79	85	-265		Malaysia	45
46			Myanmar	1	1	0	1	0	0	-1	0	0	0	0	0	0	0	0		Myanmar	46
47			Filipina	14	17	15	0	5	2	104	15	-4	3	4	17	52	-45	77		Philippines	47
48			Singapura	9.413	10.334	6.316	4.177	5.343	924	9.769	1.266	1.946	613	1.353	5.177	2.554	2.873	3.531		Singapore	48
49			Thailand	-232	164	1.137	3.208	2.077	-182	-127	7	11	24	584	626	157	125	871		Thailand	49
50			Vietnam	20	21	23	126	3	-2	2	3	-1	-2	4	4	-1	7	-2		Vietnam	50
"""

# Function to map quarters sequentially
def map_quarters_sequential(header_line, base_year=2020):
    headers = re.split(r'\t+|\s{2,}', header_line.strip())
    headers = [h for h in headers if h]

    quarter_mapping = []
    current_year = base_year
    current_quarter = ''

    for part in headers:
        if 'Q' not in part:
            continue

        quarter = part.replace('*', '').strip()

        if not current_quarter:
            # First quarter
            quarter_mapping.append((current_year, quarter))
            current_quarter = quarter
            continue

        # Determine if we need to increment the year
        if quarter == 'Q1' and current_quarter == 'Q4':
            # Transition from Q4 to Q1, increment year
            current_year += 1
        elif quarter == 'Q1' and current_quarter == 'Q1':
            # Repeated Q1, likely next year
            current_year += 1
        elif quarter == 'Q2' and current_quarter == 'Q4':
            # Transition from Q4 to Q2, increment year (if applicable)
            current_year += 1
        elif quarter == 'Q3' and current_quarter == 'Q4':
            # Transition from Q4 to Q3, increment year (if applicable)
            current_year += 1
        # Add more conditions if your data has non-standard quarter transitions

        # Assign mapped year and quarter
        quarter_mapping.append((current_year, quarter))

        # Update current_quarter
        current_quarter = quarter

    return quarter_mapping

def insert_economic_sector_data(data_str):
    lines = data_str.strip().split('\n')
    if not lines:
        print("No data found.")
        return
    
    current_sector = None
    base_year = 2020
    quarter_mapping = []

    # --- Parse header to build quarter_mapping ---
    header_line = lines[0]
    header_parts = re.split(r'\t+|\s{2,}', header_line.strip())
    header_parts = [part for part in header_parts if part]
    
    for part in header_parts:
        if 'Q' in part:
            asterisks = part.count('*')
            quarter = part.replace('*', '')
            mapped_year = base_year + asterisks
            quarter_mapping.append((mapped_year, quarter))
    
    print("Quarter Mapping:", quarter_mapping)

    # --- Parse rows ---
    for line in lines[1:]:
        parts = re.split(r'\t+|\s{2,}', line.strip())
        parts = [part for part in parts if part]
        if len(parts) < 3:
            continue
        
        # Example data structure assumption:
        # 0 -> row_number
        # 1 -> local_name (either sector or country)
        # 2..-2 -> numeric values
        # -2 -> english_name
        # -1 -> identifier
        row_number = parts[0]
        local_name = parts[1].strip()
        values = parts[2:-2]
        english_name = parts[-2].strip()
        identifier = parts[-1].strip()
        
        # Determine if row is sector or country
        if english_name.lower() != local_name.lower():
            # It's a sector
            current_sector = english_name
            continue
        else:
            # It's a country
            country = english_name
        
        # Insert/update data
        for idx, value in enumerate(values):
            if idx >= len(quarter_mapping):
                break
            year_q, quarter = quarter_mapping[idx]
            
            # Convert value to float or None
            value_clean = value.replace('.', '').replace(',', '.').strip()
            if value_clean in ('-', ''):
                numeric_value = None
            else:
                try:
                    numeric_value = float(value_clean)
                except ValueError:
                    numeric_value = None
            
            # Check if record exists (year, quarter, sector, country)
            existing_record = session.query(EconomicSectorData).filter_by(
                year=year_q,
                quarter=quarter,
                sector=current_sector if current_sector else "Unknown Sector",
                country=country
            ).first()
            
            if existing_record:
                # Update (Upsert)
                existing_record.value = numeric_value
            else:
                # Create new
                new_record = EconomicSectorData(
                    year=year_q,
                    quarter=quarter,
                    sector=current_sector if current_sector else "Unknown Sector",
                    country=country,
                    value=numeric_value
                )
                session.add(new_record)

    # Commit after processing all rows
    try:
        session.commit()
        print("Data inserted/updated successfully.")
    except IntegrityError as e:
        session.rollback()
        print(f"IntegrityError occurred: {e}")

insert_economic_sector_data(data)


