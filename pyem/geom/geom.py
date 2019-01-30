# Copyright (C) 2018 Daniel Asarnow
# University of California, San Francisco
#
# Library of miscellaneous utility functions.
# See help text and README file for more information.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np
from .quat import distq
from .quat import meanq
from .quat_numba import qslerp
from .quat_numba import qconj
from .quat_numba import qtimes
from .quat_numba import dqtimes
from .quat_numba import dqconj


def double_center(arr, reference=None, inplace=False):
    assert arr.ndim == 2
    if reference is None:
        mu0 = np.mean(arr, axis=0, keepdims=True)
        mu = np.mean(arr)
    else:
        mu0 = np.mean(reference, axis=0, keepdims=True)
        mu = np.mean(reference)
    mu1 = np.mean(arr, axis=1, keepdims=True)
    if inplace:
        arr -= mu0
        arr -= mu1
        arr += mu
    else:
        arr = arr - mu0
        arr -= mu1
        arr += mu
    return arr


def isrotation(r, tol=1e-6):
    """Check for valid rotation matrix"""
    check = np.identity(3, dtype=r.dtype) - np.dot(r.T, r)
    if tol is None:
        return check
    return np.linalg.norm(check) < tol


def qslerp_mult_balanced(keyq, steps_per_deg=10):
    qexp = []
    for i in range(0, len(keyq) - 1):
        ninterp = np.round(np.rad2deg(2 * distq(keyq[i], keyq[i + 1])) * steps_per_deg)
        for t in np.arange(0, 1, 1 / ninterp):
            qexp.append(qslerp(keyq[i], keyq[i + 1], t))
    qexp.append(keyq[-1])
    return np.array(qexp)


def findkeyq(qarr, kpcs, nkey=10, pc_cyl_ptile=25, pc_ptile=99, pc=0):
    otherpcs = list(set(np.arange(kpcs.shape[1])) - {pc})
    pcr = np.sqrt(np.sum(kpcs[:, otherpcs] ** 2, axis=1))
    mask = (pcr < np.percentile(pcr, pc_cyl_ptile)) & (
                np.abs(kpcs[:, pc]) < np.percentile(np.abs(kpcs[:, pc]), pc_ptile))
    mn, mx = np.min(kpcs[mask, pc]), np.max(kpcs[mask, pc])
    bins = np.linspace(mn, mx, nkey)
    idx = np.digitize(kpcs[mask, pc], bins) - 1
    uidx, uidxcnt = np.unique(idx, return_counts=True)
    keyq = []
    for i in uidx[uidxcnt >= 10]:
        kq = meanq(qarr[mask, :][idx == i, :])
        keyq.append(kq)
    return np.array(keyq)


def dualquat(q, t):
    assert q.shape[0] == t.shape[0]
    dq = np.zeros(q.shape, dtype=np.complex128)
    dq.real = q
    dq.imag[:, 1:] = t
    dq.imag = qtimes(dq.imag, dq.real) * 0.5
    return dq


def dq2sc(q):
    theta = 2 * np.arccos(q[:, 0].real)
    nr = 1 / np.linalg.norm(q[:, 1:].real, axis=1)
    d = -2 * q[:, 0].imag * nr
    l = q[:, 1:].real * nr
    m = (q[:, 1:].imag - l * d * q[:, 0].real * 0.5) * nr
    return theta, d, l, m


def dqdist(q1, q2):
    q = dqtimes(dqconj(q1), q2)
    theta, d, l, m = dq2sc(q)
    r2 = np.sum(m**2)
    return np.sqrt(d**2 + theta**2 * r2)