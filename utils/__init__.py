"""
Copyright (C) 2017, 申瑞珉 (Ruimin Shen)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
import importlib
import inspect
import numpy as np
import matplotlib.patches as patches
import tensorflow as tf
import sympy


def get_cachedir(config):
    basedir = os.path.expanduser(os.path.expandvars(config.get('config', 'basedir')))
    name = os.path.basename(config.get('cache', 'names'))
    return os.path.join(basedir, 'cache', name)


def get_logdir(config):
    basedir = os.path.expanduser(os.path.expandvars(config.get('config', 'basedir')))
    model = config.get('config', 'model')
    inference = config.get(model, 'inference')
    name = os.path.basename(config.get('cache', 'names'))
    return os.path.join(basedir, model, inference, name)


def get_inference(config):
    model = config.get('config', 'model')
    return getattr(importlib.import_module('.'.join(['model', model, 'inference'])), config.get(model, 'inference'))


def get_downsampling(config):
    model = config.get('config', 'model')
    return getattr(importlib.import_module('.'.join(['model', model, 'inference'])), config.get(model, 'inference').upper() + '_DOWNSAMPLING')


def calc_cell_width_height(config, width, height):
    downsampling_width, downsampling_height = get_downsampling(config)
    assert width % downsampling_width == 0
    assert height % downsampling_height == 0
    return width // downsampling_width, height // downsampling_height


def draw_labels(ax, names, width, height, cell_width, cell_height, mask, prob, coords, xy_min, xy_max, areas, color='red', rtol=1e-3):
    plots = []
    for i, (_mask, _prob, _coords, _xy_min, _xy_max, _areas) in enumerate(zip(mask, prob, coords, xy_min, xy_max, areas)):
        _mask = _mask.reshape([])
        _coords = _coords.reshape([-1])
        if np.any(_mask) > 0:
            iy = i // cell_width
            ix = i % cell_width
            plots.append(ax.add_patch(patches.Rectangle((ix * width / cell_width, iy * height / cell_height), width / cell_width, height / cell_height, linewidth=0, facecolor=color, alpha=.2)))
            name = names[np.argmax(_prob)]
            #check coords
            offset_x, offset_y, _w_sqrt, _h_sqrt = _coords
            cell_x, cell_y = ix + offset_x, iy + offset_y
            x, y = cell_x * width / cell_width, cell_y * height / cell_height
            _w, _h = _w_sqrt * _w_sqrt, _h_sqrt * _h_sqrt
            w, h = _w * width, _h * height
            x_min, y_min = x - w / 2, y - h / 2
            plots.append(ax.add_patch(patches.Rectangle((x_min, y_min), w, h, linewidth=1, edgecolor=color, facecolor='none')))
            plots.append(ax.annotate(name, (x_min, y_min), color=color))
            #check offset_xy_min and xy_max
            wh = _xy_max - _xy_min
            assert np.all(wh >= 0)
            np.testing.assert_allclose(wh / [cell_width, cell_height], [[_w, _h]], rtol=rtol)
            np.testing.assert_allclose(_xy_min + wh / 2, [[offset_x, offset_y]], rtol=rtol)
    return plots


def match_trainable_variables(pattern):
    prog = re.compile(pattern)
    return [v for v in tf.trainable_variables() if prog.match(v.op.name)]


def match_tensor(pattern):
    prog = re.compile(pattern)
    return [op.values()[0] for op in tf.get_default_graph().get_operations() if op.values() and prog.match(op.name)]


def get_factor2(x):
    factors = sympy.divisors(x)
    if len(factors) % 2 == 0:
        i = int(len(factors) / 2)
        return factors[i], factors[i - 1]
    else:
        i = len(factors) // 2
        return factors[i], factors[i]
