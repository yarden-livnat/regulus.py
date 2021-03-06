import numpy as np
from sklearn import linear_model as lm


def fitness(context, node):
    if len(node.data.y) < 2:
        return None
    return context['model'][node].score(node.data.x, node.data.y)


def stepwise_fitness(context, node):
    fitness = []
    coefficients = np.fabs(context['model'][node].coef_)
    sorted_dims = np.argsort(coefficients)
    for i in range(len(sorted_dims)):
        subspace = sorted_dims[:(i+1)]
        model = lm.LinearRegression()
        X = node.data.x[:, subspace]
        Y = node.data.y
        model.fit(X, Y)
        fitness.append((sorted_dims[i], model.score(X, Y)))
    return fitness


def relative_fitness(context, has_model, has_pts):
    if len(has_pts.data.y) < 2:
        return 0
    return context['model'][has_model].score(has_pts.data.x, has_pts.data.y)


def parent_fitness(context, node):
    if node.id == -1 or node.parent.id == -1:
        return None
    return context['relative_fitness'][node.parent, node]


def child_fitness(context, node):
    if node.id == -1 or node.parent.id == -1:
        return None
    return context['relative_fitness'][node, node.parent]


def shared_fitness(context, node):
    model = context['shared_model'][node]
    if model is None or len(node.data.y) < 2:
        return None
    return model.score(node.data.x, node.data.y)



