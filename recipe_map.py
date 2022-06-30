import networkx as nx
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
from typing import List, Dict
import pandas as pd
import math
from IPython.display import display

class ArgParser:
    def __init__(self, prompt):
        self.prompt = prompt

    def split_input(self, prompt):
        lines = [x for x in prompt.split('\n') if x]
        goal = lines.pop()
        return lines, goal
        
    def split_recipe(self, line):
        rem = [x.strip() for x in line.split('=')]
        assert len(rem) == 2, 'Only 1 equals expected'
        product = rem[0]
        ings = self.split_commas(rem[1])
        return product, ings

    def split_commas(self, line):
        return [x.strip() for x in line.split(',')]

    def split_item_count(self, selection):
        words = selection.split()
        try:
            num = int(words[0])
            ing = ' '.join(words[1:])
        except ValueError:
            num = 1
            ing = selection
        finally:
            return ing, num

    def parse_to_graph(self):
        lines, goal = self.split_input(self.prompt)
        dg = nx.DiGraph()
        for line in lines:
            product, ings = self.split_recipe(line)
            prod, count = self.split_item_count(product)
            dg.add_node(prod, yield_per_craft=count)
            for ing in ings:
                name, amount = self.split_item_count(ing)
                dg.add_edge(name, prod, required_per_craft=amount)
            
        for ing in self.split_commas(goal):
            item, count = self.split_item_count(ing)
            dg.add_edge(item, 'GOAL', required_per_craft=count)

        return dg

class RecipeMap:
    def __init__(self, dg):
        self.dg = dg

    def calc_total_required_for_goal_nodes(self):
        for from_node, to_node in self.dg.in_edges('GOAL'):
            required_per_craft = self.dg.get_edge_data(from_node, to_node)['required_per_craft']
            self.dg[from_node][to_node]['total_required'] = required_per_craft

    def calc_total_required_for_node(self, node_name):
        total_required = self.dg.out_degree(node_name, 'total_required')
        yield_per_craft = self.dg.nodes[node_name]['yield_per_craft']
        craft_x_times = math.ceil(total_required / yield_per_craft)

        for from_node, to_node in self.dg.in_edges(node_name):
            required_per_craft = self.dg.get_edge_data(from_node, to_node)['required_per_craft']
            self.dg[from_node][to_node]['total_required'] = required_per_craft * craft_x_times

    def evaluate(self, graph_func=nx.planar_layout):
        self.filter_out_unused_nodes()
        self.calc_total_required_for_goal_nodes()
        for node_name in self.reverse_topo():
            if self.dg.in_degree(node_name) == 0 or self.dg.out_degree(node_name) == 0:
                continue

            self.calc_total_required_for_node(node_name)
        self.print_graph('total_required', graph_func)
        return self.get_order()
        
    def filter_out_unused_nodes(self):
        check_nodes = [node for node in self.dg.nodes if node != 'GOAL']
        
        while check_nodes:
            node = check_nodes.pop()
            if self.dg.out_degree(node) == 0:
                for in_node, out_node in self.dg.in_edges(node):
                    check_nodes.append(in_node)
                self.dg.remove_node(node)

    def reverse_topo(self):
        return reversed(list(nx.topological_sort(self.dg)))

    def print_graph(self, attr='required_per_craft', graph_func=nx.planar_layout):
        plt.rcParams["figure.figsize"] = (12,8)

        pos = graph_func(self.dg)
        nx.draw(self.dg, pos, with_labels=True, edge_color='black', width=1, linewidth=1,node_size=500,node_color='pink',alpha=0.9)
        labels = nx.get_edge_attributes(self.dg, attr)
        nx.draw_networkx_edge_labels(self.dg, pos, edge_labels=labels)
        plt.show()

    def get_order(self, sep=True):
        dic = defaultdict(list)
        for node_name in nx.topological_sort(self.dg):
            total_required = self.dg.out_degree(node_name, 'total_required')
            ingredients_to_make = self.dg.in_degree(node_name, 'total_required')
            is_raw_ingredient = ingredients_to_make != 0
            dic['Item'].append(node_name)
            dic['Count'].append(total_required)
            dic['Crafted'].append(is_raw_ingredient)
        if not sep:
            return pd.DataFrame(dic)
        else:
            df = pd.DataFrame(dic)
            print('Materials Required: ')
            display(df[df['Crafted']==False][['Item', 'Count']])
            print('\nCrafting Order: ')
            display(df[df['Crafted']==True][['Item', 'Count']])
        
    