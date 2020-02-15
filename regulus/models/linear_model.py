from .null_model import NullModel
from sklearn import linear_model as lm


def linear_model(context, node):
    partition = node.data
    if partition.y.size < 2:
        return NullModel()
    model = lm.LinearRegression()
    model.fit(partition.x, partition.y)
    return model


def model_of(klass, **kwargs):
    def _create(context, node):
        partition = node.data
        if partition.y.size < 2:
            return
        model = klass(**kwargs)
        model.fit(partition.x, partition.y)
        return model

    return _create


def dim_models(context, node):
    partition = node.data
    if partition.y.size < 2:
        return [NullModel() for d in partition.x.columns]

    models = [lm.LinearRegression().fit(partition.x[[d]], partition.y) for d in partition.x.columns]
    return models
