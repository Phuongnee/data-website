import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime
from typing import Dict, Tuple


def extract_common_name(text):
    """Extract common name from text that is typically in parentheses."""
    match = re.search(r"\((.*?)\)", text)
    return match.group(1) if match else ""


def extract_family_name(text):
    """Extract family name by taking the first word ending in 'idae'."""
    words = text.split()
    for word in words:
        if word.endswith("idae"):
            return word
    return ""


def clean_text(text):
    """Clean text by removing citations, extra spaces, and other unwanted characters."""
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s*[A-Za-z\s.]+,\s*\d+", "", text)
    text = " ".join(text.split())
    return text.strip()


def get_family_url(li_element):
    """Extract Wikipedia URL from a family list item."""
    link = li_element.find("a")
    if link and "href" in link.attrs:
        return "https://en.wikipedia.org" + link["href"]
    return None


def extract_temporal_range(soup) -> Dict[str, any]:
    """Extract temporal range information from the page."""
    temporal_data = {
        "temporal_range": "",
        "earliest_period": "",
        "latest_period": "",
        "earliest_ma": None,  # Million years ago
        "latest_ma": None,
    }

    # Geological periods with approximate dates (in millions of years ago)
    geological_periods = {
        "quaternary": (0, 2.58),
        "holocene": (0, 0.0117),
        "pleistocene": (0.0117, 2.58),
        "neogene": (2.58, 23.03),
        "paleogene": (23.03, 66),
        "cretaceous": (66, 145),
        "jurassic": (145, 201.3),
        "triassic": (201.3, 251.9),
        "permian": (251.9, 298.9),
        "carboniferous": (298.9, 358.9),
        "devonian": (358.9, 419.2),
        "silurian": (419.2, 443.8),
        "ordovician": (443.8, 485.4),
        "cambrian": (485.4, 541),
        "recent": (0, 0.0117),  # Same as Holocene
    }

    # First try to find temporal range in infobox
    infobox = soup.find("table", class_="infobox")
    if infobox:
        for row in infobox.find_all("tr"):
            if "Temporal range" in row.get_text():
                temporal_data["temporal_range"] = clean_text(
                    row.get_text().replace("Temporal range", "")
                )
                break

    # If not found in infobox, look in the first few paragraphs
    if not temporal_data["temporal_range"]:
        intro_paras = soup.find_all("p", limit=3)
        for para in intro_paras:
            text = para.get_text().lower()
            if any(period in text for period in geological_periods.keys()):
                temporal_data["temporal_range"] = clean_text(para.get_text())
                break

    # Process the temporal range text to find periods
    if temporal_data["temporal_range"]:
        text = temporal_data["temporal_range"].lower()
        found_periods = []

        for period, (start, end) in geological_periods.items():
            if period in text:
                found_periods.append((period, start, end))

        if found_periods:
            # Sort by start date (oldest to newest)
            found_periods.sort(key=lambda x: x[2], reverse=True)

            # Set earliest period
            temporal_data["earliest_period"] = found_periods[0][0].title()
            temporal_data["earliest_ma"] = found_periods[0][2]

            # Set latest period
            temporal_data["latest_period"] = found_periods[-1][0].title()
            temporal_data["latest_ma"] = found_periods[-1][1]

    return temporal_data


def extract_distribution_and_habitat(soup):
    """Extract distribution and habitat information."""
    regions = {
        "pacific": 0,
        "atlantic": 0,
        "indian": 0,
        "arctic": 0,
        "tropical": 0,
        "temperate": 0,
        "coastal": 0,
        "deep_water": 0,
    }

    habitat_types = {
        "reef": 0,
        "pelagic": 0,
        "benthic": 0,
        "shallow": 0,
        "continental_shelf": 0,
        "oceanic": 0,
        "coastal": 0,
    }

    # Look for distribution and habitat information in various sections
    sections = soup.find_all(
        ["h2", "h3"], string=re.compile(r"Distribution|Habitat|Range")
    )
    distribution_text = ""

    for section in sections:
        next_p = section.find_next("p")
        if next_p:
            text = clean_text(next_p.get_text().lower())
            distribution_text += text + " "

            # Check for regions
            for region in regions:
                if region.replace("_", " ") in text:
                    regions[region] = 1

            # Check for habitat types
            for habitat in habitat_types:
                if habitat.replace("_", " ") in text:
                    habitat_types[habitat] = 1

    # Extract depth information
    depth_pattern = r"(\d+)(?:\s*[-–]\s*(\d+))?\s*(?:m|meters)"
    depth_matches = re.findall(depth_pattern, distribution_text)
    min_depth = max_depth = None

    if depth_matches:
        depths = []
        for match in depth_matches:
            if match[0]:
                depths.append(int(match[0]))
            if match[1]:
                depths.append(int(match[1]))
        if depths:
            min_depth = min(depths)
            max_depth = max(depths)

    return {
        "distribution_text": distribution_text.strip(),
        "regions": regions,
        "habitat_types": habitat_types,
        "min_depth": min_depth,
        "max_depth": max_depth,
    }


def extract_page_metrics(soup, url):
    """Extract metrics from the family page."""
    metrics = {
        "page_length": len(str(soup)),
        "reference_count": len(soup.find_all("sup", class_="reference")),
        "image_count": len(soup.find_all("img")),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "url": url,
    }

    # Conservation status
    status_hierarchy = {
        "Critically Endangered": 5,
        "Endangered": 4,
        "Vulnerable": 3,
        "Near Threatened": 2,
        "Least Concern": 1,
    }

    conservation_status = "Unknown"
    conservation_level = 0

    for status, level in status_hierarchy.items():
        if soup.find(string=re.compile(status, re.IGNORECASE)):
            conservation_status = status
            conservation_level = level
            break

    metrics["conservation_status"] = conservation_status
    metrics["conservation_level"] = conservation_level

    # Get temporal range
    temporal_data = extract_temporal_range(soup)
    metrics.update(temporal_data)

    # Get distribution and habitat information
    distribution_info = extract_distribution_and_habitat(soup)
    metrics.update(distribution_info["regions"])
    metrics.update(distribution_info["habitat_types"])
    metrics["geographic_distribution"] = distribution_info["distribution_text"]
    metrics["min_depth"] = distribution_info["min_depth"]
    metrics["max_depth"] = distribution_info["max_depth"]

    return metrics


def scrape_species_from_family(url):
    """Scrape species and additional metrics from a family's Wikipedia page."""
    try:
        print(f"Fetching species from {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        species_list = []

        # Look for italicized text which usually indicates scientific names
        for italics in soup.find_all("i"):
            species_name = clean_text(italics.get_text())
            if (
                species_name and len(species_name.split()) == 2
            ):  # Only get binomial names
                species_list.append(species_name)

        # Remove duplicates while preserving order
        species_list = list(dict.fromkeys(species_list))

        # Get additional metrics
        metrics = extract_page_metrics(soup, url)
        metrics["species_count"] = len(species_list)

        return species_list, metrics

    except Exception as e:
        print(f"Error scraping species from {url}: {e}")
        return [], {}


def scrape_shark_classification(html_content):
    """Scrapes shark classification data including Orders, Families, and Species."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        classification_data = []
        current_order = ""
        order_number = 0

        headings = soup.find_all(["h3"])

        for heading in headings:
            if "Order" in heading.get_text():
                current_order = heading.get_text().strip()
                current_order = clean_text(current_order)
                current_order = current_order.replace("Order ", "")
                order_number += 1
                family_number = 0

                next_ul = heading.find_next("ul")
                if next_ul:
                    for li in next_ul.find_all("li", recursive=False):
                        text = li.get_text().strip()
                        if "Family" in text:
                            family_number += 1
                            family_name = extract_family_name(text)
                            common_name = extract_common_name(text)

                            family_url = get_family_url(li)
                            species_list = []
                            family_metrics = {}
                            if family_url and family_name:
                                time.sleep(1)
                                species_list, family_metrics = (
                                    scrape_species_from_family(family_url)
                                )

                            if current_order and family_name:
                                entry = {
                                    "Order": current_order,
                                    "Order_Number": order_number,
                                    "Family": family_name,
                                    "Family_Number": family_number,
                                    "Family_Common_Name": common_name,
                                    "Species": species_list,
                                    **family_metrics,
                                }
                                classification_data.append(entry)

        return classification_data

    except Exception as e:
        print(f"Error processing the HTML content: {e}")
        return None


if __name__ == "__main__":
    print("Scraping shark classification data from Wikipedia...")

    try:
        url = "https://en.wikipedia.org/wiki/Galeomorphii"
        response = requests.get(url)
        response.raise_for_status()

        results = scrape_shark_classification(response.text)

        if results:
            # Create visualization-optimized DataFrame
            hierarchy_rows = []
            for entry in results:
                if entry["Species"]:
                    for species in entry["Species"]:
                        row = {
                            # Hierarchical Data
                            "Order": entry["Order"],
                            "Order_Number": entry["Order_Number"],
                            "Family": entry["Family"],
                            "Family_Number": entry["Family_Number"],
                            "Family_Common_Name": entry["Family_Common_Name"],
                            "Species": species,
                            # Counts and Metrics
                            "Species_Count": entry.get("species_count", 0),
                            "Reference_Count": entry.get("reference_count", 0),
                            "Image_Count": entry.get("image_count", 0),
                            "Page_Length": entry.get("page_length", 0),
                            # Conservation Data
                            "Conservation_Status": entry.get(
                                "conservation_status", "Unknown"
                            ),
                            "Conservation_Level": entry.get("conservation_level", 0),
                            # Temporal Data
                            "Temporal_Range": entry.get("temporal_range", ""),
                            "Earliest_Period": entry.get("earliest_period", ""),
                            "Latest_Period": entry.get("latest_period", ""),
                            "Earliest_MA": entry.get("earliest_ma", None),
                            "Latest_MA": entry.get("latest_ma", None),
                            "Age_Range_MA": (entry.get("earliest_ma", 0) or 0)
                            - (entry.get("latest_ma", 0) or 0),
                            # Depth Data
                            "Min_Depth": entry.get("min_depth"),
                            "Max_Depth": entry.get("max_depth"),
                            # Geographic Distribution
                            "Pacific": entry.get("pacific", 0),
                            "Atlantic": entry.get("atlantic", 0),
                            "Indian": entry.get("indian", 0),
                            "Arctic": entry.get("arctic", 0),
                            "Tropical": entry.get("tropical", 0),
                            "Temperate": entry.get("temperate", 0),
                            "Coastal": entry.get("coastal", 0),
                            "Deep_Water": entry.get("deep_water", 0),
                            # Habitat Types
                            "Reef": entry.get("reef", 0),
                            "Pelagic": entry.get("pelagic", 0),
                            "Benthic": entry.get("benthic", 0),
                            "Continental_Shelf": entry.get("continental_shelf", 0),
                            "Oceanic": entry.get("oceanic", 0),
                            # Aggregate Counts
                            "Region_Count": sum(
                                [
                                    entry.get("pacific", 0),
                                    entry.get("atlantic", 0),
                                    entry.get("indian", 0),
                                    entry.get("arctic", 0),
                                ]
                            ),
                            "Habitat_Count": sum(
                                [
                                    entry.get("reef", 0),
                                    entry.get("pelagic", 0),
                                    entry.get("benthic", 0),
                                    entry.get("continental_shelf", 0),
                                    entry.get("oceanic", 0),
                                    entry.get("coastal", 0),
                                ]
                            ),
                            # Metadata
                            "Last_Updated": entry.get("last_updated", ""),
                            "Wikipedia_URL": entry.get("url", ""),
                        }
                        hierarchy_rows.append(row)

            if hierarchy_rows:
                df = pd.DataFrame(hierarchy_rows)

                print("\nClassification Summary:")
                print(f"Total Orders: {len(df['Order'].unique())}")
                print(f"Total Families: {len(df['Family'].unique())}")
                print(f"Total Species: {len(df)}")

                # Save main hierarchical data
                df.to_csv("shark_classification_rawgraphs.csv", index=False)

                # Create and save family-level summary
                family_summary = (
                    df.groupby(["Order", "Family"])
                    .agg(
                        {
                            "Species_Count": "first",
                            "Conservation_Level": "first",
                            "Region_Count": "first",
                            "Habitat_Count": "first",
                            "Reference_Count": "first",
                            "Image_Count": "first",
                            "Earliest_Period": "first",
                            "Latest_Period": "first",
                            "Earliest_MA": "first",
                            "Latest_MA": "first",
                            "Age_Range_MA": "first",
                            "Min_Depth": "first",
                            "Max_Depth": "first",
                            "Pacific": "first",
                            "Atlantic": "first",
                            "Indian": "first",
                            "Arctic": "first",
                        }
                    )
                    .reset_index()
                )

                family_summary.to_csv("shark_families_distribution.csv", index=False)

                print("\nFiles created:")
                print(
                    "1. shark_classification_rawgraphs.csv - Complete hierarchical data"
                )
                print(
                    "2. shark_families_distribution.csv - Family-level distribution summary"
                )

                # Print temporal range summary
                print("\nTemporal Range Summary:")
                earliest = df[df["Earliest_MA"].notna()]["Earliest_MA"].max()
                latest = df[df["Latest_MA"].notna()]["Latest_MA"].min()
                print(
                    f"Overall temporal range: {earliest} to {latest} million years ago"
                )

            else:
                print("No valid data was found to create the hierarchy.")

        else:
            print("No data was found to process.")

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
