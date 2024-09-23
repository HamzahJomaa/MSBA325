import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# Load your data
data = pd.read_csv("https://linked.aub.edu.lb/pkgcube/data/13e1689d0a84bc62e3e3a309c06956fc_20240902_120434.csv")

# Clean up column names by stripping any leading or trailing whitespace
data.columns = data.columns.str.strip()

# Extract the last path for the name and replace underscores with spaces
data['Name'] = data['refArea'].apply(lambda x: x.rstrip('/').split('/')[-1].replace('_', ' '))

# **Group Towns by Ref Area**
# Clean 'Town' column (remove leading/trailing whitespace)

# Create a mapping of Ref Area to Towns
refarea_towns = data.groupby('Name')['Town'].unique().reset_index()
refarea_towns['Towns'] = refarea_towns['Town'].apply(lambda x: ', '.join(sorted(x)))
refarea_towns = refarea_towns[['Name', 'Towns']]

# **Create a mapping of Name to refArea**
refarea_links = data[['Name', 'refArea']].drop_duplicates()

# Group by 'Name' for aggregation
grouped_data = data.groupby('Name').agg(
    total_care_centers=('Total number of care centers', 'sum'),
    hospitals=('Type and size of medical resources - Hospitals', 'sum'),
    clinics=('Type and size of medical resources - Clinics', 'sum'),
    pharmacies=('Type and size of medical resources - Pharmacies', 'sum'),
    labs=('Type and size of medical resources - Labs and Radiology', 'sum'),
    medical_centers=('Type and size of medical resources - Medical Centers', 'sum'),
    exists_special_needs=('Existence of special needs care centers - exists', 'sum'),
    does_not_exist_special_needs=('Existence of special needs care centers - does not exist', 'sum'),
).reset_index()

# Merge the towns information and refArea links back into grouped_data
grouped_data = grouped_data.merge(refarea_towns, on='Name', how='left')
grouped_data = grouped_data.merge(refarea_links, on='Name', how='left')

st.title('Healthcare Resources and Special Needs Data')

# Dropdown for Ref Area selection
ref_areas = ['All'] + grouped_data["Name"].tolist()
selected_area = st.selectbox("Select a Ref Area", ref_areas)

# Filter data based on selection
if selected_area == 'All':
    dff = grouped_data.copy()
else:
    dff = grouped_data[grouped_data.Name == selected_area].copy()
    ref_area_link = dff['refArea'].iloc[0]

if not dff.empty:
        # **Display Towns in the Selected Ref Area**
    if selected_area != 'All':
                # **Scrape Data from refArea Link**
        def get_dbpedia_abstract(ref_area_link):
            # Get the resource name
            resource_name = ref_area_link.rstrip('/').split('/')[-1]
            # Build the URL for the dbpedia resource
            resource_url = f"http://dbpedia.org/data/{resource_name}.json"

            response = requests.get(resource_url)
            if response.status_code == 200:
                data = response.json()
                resource_uri = f"http://dbpedia.org/resource/{resource_name}"
                if resource_uri in data:
                    resource_data = data[resource_uri]
                    abstracts = [item['value'] for item in resource_data.get('http://dbpedia.org/ontology/abstract', []) if item['lang'] == 'en']
                    if abstracts:
                        return abstracts[0]
                    else:
                        return "No abstract found."
                else:
                    return "Resource not found in data."
            else:
                return f"Failed to retrieve data. Status code: {response.status_code}"

        st.subheader('Information about the Selected Ref Area')
        abstract = get_dbpedia_abstract(ref_area_link)
        st.write(abstract)
        
    # **1. Sort for Bar Chart: Total Number of Care Centers**
    dff_bar = dff.sort_values('total_care_centers', ascending=False)
    st.subheader('Total Number of Care Centers')
    fig_bar = px.bar(dff_bar, x='Name', y='total_care_centers', title='Total Number of Care Centers by Ref Area')
    fig_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar)

    # **2. Sort for Stacked Bar Chart: Medical Resources by Ref Area**
    # Create a total medical resources column
    dff['total_medical_resources'] = dff[['hospitals', 'clinics', 'pharmacies', 'labs', 'medical_centers']].sum(axis=1)
    dff_stacked = dff.sort_values('total_medical_resources', ascending=False)
    st.subheader('Medical Resources by Ref Area')
    fig_stacked = go.Figure(data=[
        go.Bar(name='Hospitals', x=dff_stacked['Name'], y=dff_stacked['hospitals']),
        go.Bar(name='Clinics', x=dff_stacked['Name'], y=dff_stacked['clinics']),
        go.Bar(name='Pharmacies', x=dff_stacked['Name'], y=dff_stacked['pharmacies']),
        go.Bar(name='Labs and Radiology', x=dff_stacked['Name'], y=dff_stacked['labs']),
        go.Bar(name='Medical Centers', x=dff_stacked['Name'], y=dff_stacked['medical_centers'])
    ])
    fig_stacked.update_layout(barmode='stack', title="Medical Resources by Ref Area", xaxis_tickangle=-45)
    st.plotly_chart(fig_stacked)

    # **3. Pie Chart: Existence of Special Needs Care Centers**
    st.subheader("Existence of Special Needs Care Centers")
    labels = ['Exists', 'Does not exist']
    values = [dff['exists_special_needs'].sum(), dff['does_not_exist_special_needs'].sum()]
    # Sort the labels and values based on values
    sorted_labels_values = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
    sorted_labels, sorted_values = zip(*sorted_labels_values)
    fig_pie = px.pie(values=sorted_values, names=sorted_labels, title="Existence of Special Needs Care Centers")
    st.plotly_chart(fig_pie)

    # **Display Towns in the Selected Ref Area**
    if selected_area != 'All':
        st.subheader('Towns in the Selected Ref Area')
        towns = dff['Towns'].iloc[0]
        st.write(f"**{selected_area}** includes the following towns:")
        towns_list = towns.split(',')  # Assuming towns are comma-separated
        st.markdown('\n'.join([f"- {town.strip()}" for town in towns_list]))

else:
    st.warning("No data available for the selected ref area.")
