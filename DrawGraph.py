import json
import re
import networkx as nx
import plotly.graph_objects as go

DEFAULT_WEIGHT = 3

# Function: Merging json files for multiple regions
def merge_json_files(file_paths):
    merged_data = []
    for path in file_paths:
        with open(path, 'r') as file:
            data = json.load(file)["result"]
            merged_data.append(data)
    finalList = []
    for item in merged_data:
        finalList += item
    new_dict = {"result": finalList}
    return new_dict

# Function: Set attribute "Distance" for the edges of Anomaly Graph
def SetWeight(node_details, current_node, node_name, list_observations):
    findings_current = re.findall(r'\d+\.\d+|\d+', node_details[current_node][list_observations[1]])
    if (len(findings_current) > 0):
      dist_current = float(findings_current[0])
    else:
      dist_current = 0
    findings = re.findall(r'\d+\.\d+|\d+', node_details[node_name][list_observations[1]])
    if (len(findings) > 0):
      dist_node = float(findings[0])
    else:
      dist_node = 0
    weight = round(abs(dist_node - dist_current),2)
    if weight == 0:
      weight = DEFAULT_WEIGHT
    return weight

# Function: Set attribute "Distance" for the edges of Manhole Graph
def SetWeightManhole(node_details, node_name, list_general):
    findings = re.findall(r"[-+]?\d*\.*\d+", node_details[node_name][list_general[2]])
    if (len(findings) > 0):
      dist_node = float(findings[0])
    else:
      dist_node = 0
    weight = dist_node
    if weight == 0:
      weight = DEFAULT_WEIGHT
    return weight

# Function: Draw Anomaly or Manhole Graph based on isFull (True: Draw anomaly graph; False: Draw manhole graph)
# Note: list_keys are list of keywords that people want to extract information from report files.
def DrawGraph(folder_process, uploadsFolder, fileJsonPath, list_keys, isFull):
    list_observations = list_keys[0:3]
    list_general = list_keys[3:]
    # Load the JSON file
    with open(fileJsonPath, 'r') as file:
        data = json.load(file)
    # Create Graph
    G = nx.DiGraph()

    node_details = {}

    # Add Nodes and Edges into Graph
    for segment in data['result']:
        from_node = segment[list_general[0]]
        to_node = segment[list_general[1]]

        if (from_node.isspace() or to_node.isspace()):
            continue
        if (G.has_node(from_node) == False):
            node_details[from_node] = {
                list_general[0]: segment[list_general[0]],
                list_general[1]: segment[list_general[1]],
                "type": "manhole"
            }
            if (len(segment['Problems']) != 0):
                node_details[from_node][list_general[2]] = segment['Problems'][0][list_general[2]]
            else:
                node_details[from_node][list_general[2]] = DEFAULT_WEIGHT
            G.add_node(from_node, size=20, label=from_node)
        if (G.has_node(to_node) == False):
            node_details[to_node] = {
                list_general[0]: segment[list_general[0]],
                list_general[1]: segment[list_general[1]],
                "type": "manhole"
            }
            if (len(segment['Problems']) != 0):
                node_details[to_node][list_general[2]] = segment['Problems'][0][list_general[2]]
            else:
                node_details[to_node][list_general[2]] = DEFAULT_WEIGHT
            G.add_node(to_node, size=20, label=to_node)
        if isFull:
            if (len(segment['Problems']) == 0):
                G.add_edge(from_node, to_node)
            else:
                current_node = from_node
                for i in range(0, len(segment["Problems"])):
                    final_str_number = "NA"
                    res_number = [int(i) for i in segment["Problems"][i][list_observations[0]].split() if i.isdigit()]
                    if len(res_number) != 0:
                        final_str_number = ''.join(str(x) for x in res_number)
                    node_name = segment[list_general[0]] + "-" + segment[list_general[1]] + "_" + final_str_number
                    node_details[node_name] = {
                        list_observations[k]: segment["Problems"][i][list_observations[k]]
                        for k in range(0, len(list_observations))
                    }
                    for j in range(2, len(list_general)):
                        node_details[node_name][list_general[j]] = segment["Problems"][i][list_general[j]]

                    node_details[node_name]["type"] = "subnode"

                    G.add_node(node_name, size=10, label=node_name)
                    if i == len(segment["Problems"]) - 1:
                        weight = SetWeight(node_details, current_node, node_name, list_observations)
                        G.add_edge(current_node, node_name, weight=weight)
                        G.add_edge(node_name, to_node)
                    else:
                        if (G.has_edge(current_node, node_name) == False):
                            if (current_node == from_node):
                                G.add_edge(current_node, node_name)
                            else:
                                weight = SetWeight(node_details, current_node, node_name, list_observations)
                                G.add_edge(current_node, node_name, weight=weight)
                        current_node = node_name
        else:
            weight = SetWeightManhole(node_details, from_node, list_general)
            G.add_edge(from_node, to_node, weight=weight)

    # Draw Graph
    # Create node positions using spring layout, adjust `k` to spread nodes
    pos = nx.spring_layout(G, k=0.42, seed=42)

    # Extract data for plotly
    edge_x = []
    edge_y = []
    edge_labels = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)  # Break in the line
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)
        # Add edge label for later placement
        edge_labels.append(((x0 + x1) / 2, (y0 + y1) / 2, edge[2].get('weight', '')))  # Midpoint X, Y, Weight

    # Edge trace
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Node positions and hover text
    node_x = []
    node_y = []
    node_hoverinfo = []
    node_size = []
    node_color = []
    node_text = []
    node_font_size = []
    node_marker_symbol = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        # Prepare hover text for each node
        details = node_details.get(node, {})
        if details.get("type") == "subnode":
            hover_text = f"""Node: {node}<br>"""
            text_obs = ""
            for kw in list_observations:
                text_obs += kw + ":" + details.get(kw) + "<br>"
            hover_text += text_obs
            text_gen = ""
            for i in range(2, len(list_general)):
                kw = list_general[i]
                if kw in details:
                    text_gen += kw + ":" + details.get(kw) + "<br>"
            hover_text += text_gen
            node_hoverinfo.append(hover_text)
        else:
            hover_text = f"""Node: {node}<br>"""
            text_manhole = list_general[0] + ":" + details.get(list_general[0]) + "<br>" + list_general[
                1] + ":" + details.get(list_general[1])
            hover_text += text_manhole
            node_hoverinfo.append(hover_text)
        # Customize node properties based on type
        if details.get("type") == "subnode":
            node_size.append(10)
            node_color.append("blue")
            node_text.append(node)
            node_font_size.append(8)
            node_marker_symbol.append("square")
        else:
            node_size.append(20)
            node_color.append("red")
            node_text.append(node)
            node_font_size.append(12)
            node_marker_symbol.append("circle")

    # Node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        hoverinfo='text',
        hovertext=node_hoverinfo,
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=2),
            symbol=node_marker_symbol
        ),
        textfont=dict(
            size=node_font_size,
            color=node_color
        )
    )

    # Edge weight trace
    edge_label_trace = go.Scatter(
        x=[label[0] for label in edge_labels],  # X-coordinates of edge labels
        y=[label[1] for label in edge_labels],  # Y-coordinates of edge labels
        text=[f"{label[2]}" for label in edge_labels],  # Edge weights
        mode="text",
        hoverinfo="none",
        textfont=dict(size=10, color="red")
    )

    # Create the figure
    fig = go.Figure(data=[edge_trace, node_trace, edge_label_trace],
                    layout=go.Layout(
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=40),
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False)
                    ))
    if isFull:
        plotFile = folder_process + '_plot.html'
        fig.write_html(uploadsFolder + "\\" + plotFile, full_html=False)
    else:
        plotFile = folder_process + '_plot_simple.html'
        fig.write_html(uploadsFolder + "\\" + plotFile, full_html=False)
    return plotFile


# Function: Draw Manhole or Anomaly Graph for multiple regions based on isFull (True: Draw anomaly graph; False: Draw manhole graph)
# Notes: fileJsonPath includes list of jsonFile (with each jsonFile is used for storing data of graph in per region)
def DrawMultiGraph(uploadsFolder, fileJsonPath, isFull):
    data = merge_json_files(fileJsonPath)
    list_keys = list(data['result'][0]['Problems'][0].keys())[0:3] + list(data['result'][0].keys())[0:2] + list(data['result'][0]['Problems'][0].keys())[3:]
    list_observations = list_keys[0:3]
    list_general = list_keys[3:]
    # Create Graph
    G = nx.DiGraph()

    node_details = {}

    # Add Nodes and Edges into Graph
    for segment in data['result']:
        from_node = segment[list_general[0]]
        to_node = segment[list_general[1]]

        if (from_node.isspace() or to_node.isspace()):
            continue
        if (G.has_node(from_node) == False):
            node_details[from_node] = {
                list_general[0]: segment[list_general[0]],
                list_general[1]: segment[list_general[1]],
                "type": "manhole"
            }
            if (len(segment['Problems']) != 0):
                node_details[from_node][list_general[2]] = segment['Problems'][0][list_general[2]]
            else:
                node_details[from_node][list_general[2]] = DEFAULT_WEIGHT
            G.add_node(from_node, size=20, label=from_node)
        if (G.has_node(to_node) == False):
            node_details[to_node] = {
                list_general[0]: segment[list_general[0]],
                list_general[1]: segment[list_general[1]],
                "type": "manhole"
            }
            if (len(segment['Problems']) != 0):
                node_details[to_node][list_general[2]] = segment['Problems'][0][list_general[2]]
            else:
                node_details[to_node][list_general[2]] = DEFAULT_WEIGHT
            G.add_node(to_node, size=20, label=to_node)
        if isFull:
            if (len(segment['Problems']) == 0):
                G.add_edge(from_node, to_node)
            else:
                current_node = from_node
                for i in range(0, len(segment["Problems"])):
                    node_name = segment[list_general[0]] + "-" + segment[list_general[1]] + "_" + ''.join(
                        [char for char in segment["Problems"][i][list_observations[0]] if char.isdigit()])
                    node_details[node_name] = {
                        list_observations[k]: segment["Problems"][i][list_observations[k]]
                        for k in range(0, len(list_observations))
                    }
                    for j in range(2, len(list_general)):
                        node_details[node_name][list_general[j]] = segment["Problems"][i][list_general[j]]

                    node_details[node_name]["type"] = "subnode"

                    G.add_node(node_name, size=10, label=node_name)
                    if i == len(segment["Problems"]) - 1:
                        weight = SetWeight(node_details, current_node, node_name, list_observations)
                        G.add_edge(current_node, node_name, weight=weight)
                        G.add_edge(node_name, to_node)
                    else:
                        if (G.has_edge(current_node, node_name) == False):
                            if (current_node == from_node):
                                G.add_edge(current_node, node_name)
                            else:
                                weight = SetWeight(node_details, current_node, node_name, list_observations)
                                G.add_edge(current_node, node_name, weight=weight)
                        current_node = node_name
        else:
            weight = SetWeightManhole(node_details, from_node, list_general)
            G.add_edge(from_node, to_node, weight=weight)

    # Draw Graph
    # Create node positions using spring layout, adjust `k` to spread nodes
    pos = nx.spring_layout(G, k=0.42, seed=42)

    # Extract data for plotly
    edge_x = []
    edge_y = []
    edge_labels = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)  # Break in the line
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)
        # Add edge label for later placement
        edge_labels.append(((x0 + x1) / 2, (y0 + y1) / 2, edge[2].get('weight', '')))  # Midpoint X, Y, Weight

    # Edge trace
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Node positions and hover text
    node_x = []
    node_y = []
    node_hoverinfo = []
    node_size = []
    node_color = []
    node_text = []
    node_font_size = []
    node_marker_symbol = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        # Prepare hover text for each node
        details = node_details.get(node, {})
        if details.get("type") == "subnode":
            hover_text = f"""Node: {node}<br>"""
            text_obs = ""
            for kw in list_observations:
                text_obs += kw + ":" + details.get(kw) + "<br>"
            hover_text += text_obs
            text_gen = ""
            for i in range(2, len(list_general)):
                kw = list_general[i]
                if kw in details:
                    text_gen += kw + ":" + details.get(kw) + "<br>"
            hover_text += text_gen
            node_hoverinfo.append(hover_text)
        else:
            hover_text = f"""Node: {node}<br>"""
            text_manhole = list_general[0] + ":" + details.get(list_general[0]) + "<br>" + list_general[
                1] + ":" + details.get(list_general[1])
            hover_text += text_manhole
            node_hoverinfo.append(hover_text)
        # Customize node properties based on type
        if details.get("type") == "subnode":
            node_size.append(10)
            node_color.append("blue")
            node_text.append(node)
            node_font_size.append(8)
            node_marker_symbol.append("square")
        else:
            node_size.append(20)
            node_color.append("red")
            node_text.append(node)
            node_font_size.append(12)
            node_marker_symbol.append("circle")

    # Node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        hoverinfo='text',
        hovertext=node_hoverinfo,
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=2),
            symbol=node_marker_symbol
        ),
        textfont=dict(
            size=node_font_size,
            color=node_color
        )
    )

    # Edge weight trace
    edge_label_trace = go.Scatter(
        x=[label[0] for label in edge_labels],  # X-coordinates of edge labels
        y=[label[1] for label in edge_labels],  # Y-coordinates of edge labels
        text=[f"{label[2]}" for label in edge_labels],  # Edge weights
        mode="text",
        hoverinfo="none",
        textfont=dict(size=10, color="red")
    )

    # Create the figure
    fig = go.Figure(data=[edge_trace, node_trace, edge_label_trace],
                    layout=go.Layout(
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=40),
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False)
                    ))
    if isFull:
        plotFile = 'final_plot.html'
        fig.write_html(uploadsFolder + "\\" + plotFile, full_html=False)
    else:
        plotFile = 'final_plot_simple.html'
        fig.write_html(uploadsFolder + "\\" + plotFile, full_html=False)
    return plotFile