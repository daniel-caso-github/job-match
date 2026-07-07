"""enrich_countries_add_profile_country

Revision ID: c7d8e9f0a1b2
Revises: fb9016b86fde
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "fb9016b86fde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (name, iso2, iso3, continent)
_COUNTRIES: list[tuple[str, str, str, str]] = [
    ("Afghanistan", "AF", "AFG", "Asia"),
    ("Albania", "AL", "ALB", "Europe"),
    ("Algeria", "DZ", "DZA", "Africa"),
    ("Andorra", "AD", "AND", "Europe"),
    ("Angola", "AO", "AGO", "Africa"),
    ("Antigua and Barbuda", "AG", "ATG", "Americas"),
    ("Argentina", "AR", "ARG", "Americas"),
    ("Armenia", "AM", "ARM", "Asia"),
    ("Australia", "AU", "AUS", "Oceania"),
    ("Austria", "AT", "AUT", "Europe"),
    ("Azerbaijan", "AZ", "AZE", "Asia"),
    ("Bahamas", "BS", "BHS", "Americas"),
    ("Bahrain", "BH", "BHR", "Asia"),
    ("Bangladesh", "BD", "BGD", "Asia"),
    ("Barbados", "BB", "BRB", "Americas"),
    ("Belarus", "BY", "BLR", "Europe"),
    ("Belgium", "BE", "BEL", "Europe"),
    ("Belize", "BZ", "BLZ", "Americas"),
    ("Benin", "BJ", "BEN", "Africa"),
    ("Bhutan", "BT", "BTN", "Asia"),
    ("Bolivia", "BO", "BOL", "Americas"),
    ("Bosnia and Herzegovina", "BA", "BIH", "Europe"),
    ("Botswana", "BW", "BWA", "Africa"),
    ("Brazil", "BR", "BRA", "Americas"),
    ("Brunei", "BN", "BRN", "Asia"),
    ("Bulgaria", "BG", "BGR", "Europe"),
    ("Burkina Faso", "BF", "BFA", "Africa"),
    ("Burundi", "BI", "BDI", "Africa"),
    ("Cabo Verde", "CV", "CPV", "Africa"),
    ("Cambodia", "KH", "KHM", "Asia"),
    ("Cameroon", "CM", "CMR", "Africa"),
    ("Canada", "CA", "CAN", "Americas"),
    ("Central African Republic", "CF", "CAF", "Africa"),
    ("Chad", "TD", "TCD", "Africa"),
    ("Chile", "CL", "CHL", "Americas"),
    ("China", "CN", "CHN", "Asia"),
    ("Colombia", "CO", "COL", "Americas"),
    ("Comoros", "KM", "COM", "Africa"),
    ("Congo", "CG", "COG", "Africa"),
    ("Costa Rica", "CR", "CRI", "Americas"),
    ("Croatia", "HR", "HRV", "Europe"),
    ("Cuba", "CU", "CUB", "Americas"),
    ("Cyprus", "CY", "CYP", "Asia"),
    ("Czech Republic", "CZ", "CZE", "Europe"),
    ("Denmark", "DK", "DNK", "Europe"),
    ("Djibouti", "DJ", "DJI", "Africa"),
    ("Dominica", "DM", "DMA", "Americas"),
    ("Dominican Republic", "DO", "DOM", "Americas"),
    ("DR Congo", "CD", "COD", "Africa"),
    ("Ecuador", "EC", "ECU", "Americas"),
    ("Egypt", "EG", "EGY", "Africa"),
    ("El Salvador", "SV", "SLV", "Americas"),
    ("Equatorial Guinea", "GQ", "GNQ", "Africa"),
    ("Eritrea", "ER", "ERI", "Africa"),
    ("Estonia", "EE", "EST", "Europe"),
    ("Eswatini", "SZ", "SWZ", "Africa"),
    ("Ethiopia", "ET", "ETH", "Africa"),
    ("Fiji", "FJ", "FJI", "Oceania"),
    ("Finland", "FI", "FIN", "Europe"),
    ("France", "FR", "FRA", "Europe"),
    ("Gabon", "GA", "GAB", "Africa"),
    ("Gambia", "GM", "GMB", "Africa"),
    ("Georgia", "GE", "GEO", "Asia"),
    ("Germany", "DE", "DEU", "Europe"),
    ("Ghana", "GH", "GHA", "Africa"),
    ("Greece", "GR", "GRC", "Europe"),
    ("Grenada", "GD", "GRD", "Americas"),
    ("Guatemala", "GT", "GTM", "Americas"),
    ("Guinea", "GN", "GIN", "Africa"),
    ("Guinea-Bissau", "GW", "GNB", "Africa"),
    ("Guyana", "GY", "GUY", "Americas"),
    ("Haiti", "HT", "HTI", "Americas"),
    ("Honduras", "HN", "HND", "Americas"),
    ("Hungary", "HU", "HUN", "Europe"),
    ("Iceland", "IS", "ISL", "Europe"),
    ("India", "IN", "IND", "Asia"),
    ("Indonesia", "ID", "IDN", "Asia"),
    ("Iran", "IR", "IRN", "Asia"),
    ("Iraq", "IQ", "IRQ", "Asia"),
    ("Ireland", "IE", "IRL", "Europe"),
    ("Israel", "IL", "ISR", "Asia"),
    ("Italy", "IT", "ITA", "Europe"),
    ("Ivory Coast", "CI", "CIV", "Africa"),
    ("Jamaica", "JM", "JAM", "Americas"),
    ("Japan", "JP", "JPN", "Asia"),
    ("Jordan", "JO", "JOR", "Asia"),
    ("Kazakhstan", "KZ", "KAZ", "Asia"),
    ("Kenya", "KE", "KEN", "Africa"),
    ("Kiribati", "KI", "KIR", "Oceania"),
    ("Kuwait", "KW", "KWT", "Asia"),
    ("Kyrgyzstan", "KG", "KGZ", "Asia"),
    ("Laos", "LA", "LAO", "Asia"),
    ("Latvia", "LV", "LVA", "Europe"),
    ("Lebanon", "LB", "LBN", "Asia"),
    ("Lesotho", "LS", "LSO", "Africa"),
    ("Liberia", "LR", "LBR", "Africa"),
    ("Libya", "LY", "LBY", "Africa"),
    ("Liechtenstein", "LI", "LIE", "Europe"),
    ("Lithuania", "LT", "LTU", "Europe"),
    ("Luxembourg", "LU", "LUX", "Europe"),
    ("Madagascar", "MG", "MDG", "Africa"),
    ("Malawi", "MW", "MWI", "Africa"),
    ("Malaysia", "MY", "MYS", "Asia"),
    ("Maldives", "MV", "MDV", "Asia"),
    ("Mali", "ML", "MLI", "Africa"),
    ("Malta", "MT", "MLT", "Europe"),
    ("Marshall Islands", "MH", "MHL", "Oceania"),
    ("Mauritania", "MR", "MRT", "Africa"),
    ("Mauritius", "MU", "MUS", "Africa"),
    ("Mexico", "MX", "MEX", "Americas"),
    ("Micronesia", "FM", "FSM", "Oceania"),
    ("Moldova", "MD", "MDA", "Europe"),
    ("Monaco", "MC", "MCO", "Europe"),
    ("Mongolia", "MN", "MNG", "Asia"),
    ("Montenegro", "ME", "MNE", "Europe"),
    ("Morocco", "MA", "MAR", "Africa"),
    ("Mozambique", "MZ", "MOZ", "Africa"),
    ("Myanmar", "MM", "MMR", "Asia"),
    ("Namibia", "NA", "NAM", "Africa"),
    ("Nauru", "NR", "NRU", "Oceania"),
    ("Nepal", "NP", "NPL", "Asia"),
    ("Netherlands", "NL", "NLD", "Europe"),
    ("New Zealand", "NZ", "NZL", "Oceania"),
    ("Nicaragua", "NI", "NIC", "Americas"),
    ("Niger", "NE", "NER", "Africa"),
    ("Nigeria", "NG", "NGA", "Africa"),
    ("North Korea", "KP", "PRK", "Asia"),
    ("North Macedonia", "MK", "MKD", "Europe"),
    ("Norway", "NO", "NOR", "Europe"),
    ("Oman", "OM", "OMN", "Asia"),
    ("Pakistan", "PK", "PAK", "Asia"),
    ("Palau", "PW", "PLW", "Oceania"),
    ("Palestine", "PS", "PSE", "Asia"),
    ("Panama", "PA", "PAN", "Americas"),
    ("Papua New Guinea", "PG", "PNG", "Oceania"),
    ("Paraguay", "PY", "PRY", "Americas"),
    ("Peru", "PE", "PER", "Americas"),
    ("Philippines", "PH", "PHL", "Asia"),
    ("Poland", "PL", "POL", "Europe"),
    ("Portugal", "PT", "PRT", "Europe"),
    ("Qatar", "QA", "QAT", "Asia"),
    ("Romania", "RO", "ROU", "Europe"),
    ("Russia", "RU", "RUS", "Europe"),
    ("Rwanda", "RW", "RWA", "Africa"),
    ("Saint Kitts and Nevis", "KN", "KNA", "Americas"),
    ("Saint Lucia", "LC", "LCA", "Americas"),
    ("Saint Vincent and the Grenadines", "VC", "VCT", "Americas"),
    ("Samoa", "WS", "WSM", "Oceania"),
    ("San Marino", "SM", "SMR", "Europe"),
    ("Sao Tome and Principe", "ST", "STP", "Africa"),
    ("Saudi Arabia", "SA", "SAU", "Asia"),
    ("Senegal", "SN", "SEN", "Africa"),
    ("Serbia", "RS", "SRB", "Europe"),
    ("Seychelles", "SC", "SYC", "Africa"),
    ("Sierra Leone", "SL", "SLE", "Africa"),
    ("Singapore", "SG", "SGP", "Asia"),
    ("Slovakia", "SK", "SVK", "Europe"),
    ("Slovenia", "SI", "SVN", "Europe"),
    ("Solomon Islands", "SB", "SLB", "Oceania"),
    ("Somalia", "SO", "SOM", "Africa"),
    ("South Africa", "ZA", "ZAF", "Africa"),
    ("South Korea", "KR", "KOR", "Asia"),
    ("South Sudan", "SS", "SSD", "Africa"),
    ("Spain", "ES", "ESP", "Europe"),
    ("Sri Lanka", "LK", "LKA", "Asia"),
    ("Sudan", "SD", "SDN", "Africa"),
    ("Suriname", "SR", "SUR", "Americas"),
    ("Sweden", "SE", "SWE", "Europe"),
    ("Switzerland", "CH", "CHE", "Europe"),
    ("Syria", "SY", "SYR", "Asia"),
    ("Taiwan", "TW", "TWN", "Asia"),
    ("Tajikistan", "TJ", "TJK", "Asia"),
    ("Tanzania", "TZ", "TZA", "Africa"),
    ("Thailand", "TH", "THA", "Asia"),
    ("Timor-Leste", "TL", "TLS", "Asia"),
    ("Togo", "TG", "TGO", "Africa"),
    ("Tonga", "TO", "TON", "Oceania"),
    ("Trinidad and Tobago", "TT", "TTO", "Americas"),
    ("Tunisia", "TN", "TUN", "Africa"),
    ("Turkey", "TR", "TUR", "Asia"),
    ("Turkmenistan", "TM", "TKM", "Asia"),
    ("Tuvalu", "TV", "TUV", "Oceania"),
    ("Uganda", "UG", "UGA", "Africa"),
    ("Ukraine", "UA", "UKR", "Europe"),
    ("United Arab Emirates", "AE", "ARE", "Asia"),
    ("United Kingdom", "GB", "GBR", "Europe"),
    ("United States", "US", "USA", "Americas"),
    ("Uruguay", "UY", "URY", "Americas"),
    ("Uzbekistan", "UZ", "UZB", "Asia"),
    ("Vanuatu", "VU", "VUT", "Oceania"),
    ("Vatican City", "VA", "VAT", "Europe"),
    ("Venezuela", "VE", "VEN", "Americas"),
    ("Vietnam", "VN", "VNM", "Asia"),
    ("Yemen", "YE", "YEM", "Asia"),
    ("Zambia", "ZM", "ZMB", "Africa"),
    ("Zimbabwe", "ZW", "ZWE", "Africa"),
]


def upgrade() -> None:
    # 1. Enriquecer tabla countries
    op.add_column("countries", sa.Column("iso2", sa.String(2), nullable=True))
    op.add_column("countries", sa.Column("iso3", sa.String(3), nullable=True))
    op.add_column("countries", sa.Column("continent", sa.String(50), nullable=True))
    op.create_index("ix_countries_iso2", "countries", ["iso2"])

    # 2. FK country_id en profiles
    op.add_column("profiles", sa.Column("country_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_profiles_country_id",
        "profiles",
        "countries",
        ["country_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3a. Actualizar entradas existentes que coincidan por nombre
    for name, iso2, iso3, continent in _COUNTRIES:
        op.execute(
            sa.text(
                "UPDATE countries SET iso2=:iso2, iso3=:iso3, continent=:continent "
                "WHERE lower(name) = lower(:name)"
            ).bindparams(iso2=iso2, iso3=iso3, continent=continent, name=name)
        )

    # 3b. Insertar países del mundo que aún no existan en la tabla
    for name, iso2, iso3, continent in _COUNTRIES:
        op.execute(
            sa.text(
                "INSERT INTO countries (name, iso2, iso3, continent) "
                "VALUES (:name, :iso2, :iso3, :continent) "
                "ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name, iso2=iso2, iso3=iso3, continent=continent)
        )


def downgrade() -> None:
    op.drop_constraint("fk_profiles_country_id", "profiles", type_="foreignkey")
    op.drop_column("profiles", "country_id")
    op.drop_index("ix_countries_iso2", table_name="countries")
    op.drop_column("countries", "continent")
    op.drop_column("countries", "iso3")
    op.drop_column("countries", "iso2")
