# -*- coding: utf-8 -*-

# define variables
from config import hp
from config import bool
from config import other

# import python modules
from os import path
from os import mkdir
import numpy as np
from mpi4py import MPI
try:
    from quippy import AtomsReader
    from quippy import farray
    from quippy import fzeros
    from quippy import frange
except ImportError:
    print 'Warning: can\'t import quippy, so can\'t calculate symmetric functions, but load them.'
    bool.CALC_INPUT = False


class LabelGenerator(object):
    def __init__(self, train_npy_dir, name):
        self.train_npy_dir = train_npy_dir
        self.name = name

    def make(self, atoms_objs, natom, nsample):
        Es = np.array([data.cohesive_energy for data in atoms_objs])
        Fs = np.array([np.array(data.force).T for data in atoms_objs]).reshape((nsample, 3*natom))
        np.save(path.join(self.train_npy_dir, self.name+'-Es.npy'), Es)
        np.save(path.join(self.train_npy_dir, self.name+'-Fs.npy'), Fs)
        return Es, Fs

    def load(self):
        Es = np.load(path.join(self.train_npy_dir, self.name+'-Es.npy'))
        Fs = np.load(path.join(self.train_npy_dir, self.name+'-Fs.npy'))
        return Es, Fs


class EFGenerator(LabelGenerator):
    pass


class InputGenerator(object):
    def __init__(self, train_npy_dir, name, Rcs, etas, Rss, lams, zetas):
        self.train_npy_dir = train_npy_dir
        self.name = name
        self.Rcs = Rcs
        self.etas = etas
        self.Rss = Rss
        self.lams = lams
        self.zetas = zetas

    def make(self, comm, size, rank, atoms_objs, natom, nsample, ninput):
        self.comm = comm
        self.atoms_objs = atoms_objs
        self.natom = natom
        self.nsample = nsample
        quo, rem = self.nsample/size, self.nsample % size
        if rank < rem:
            self.min, self.max = rank*(quo+1), (rank+1)*(quo+1)
        else:
            self.min, self.max = rank*quo+rem, (rank+1)*quo+rem

        Gs = np.empty((ninput, self.nsample, self.natom))
        dGs = np.empty((ninput, self.nsample, self.natom, 3*self.natom))

        n = 0
        for Rc in self.Rcs:
            prefix = path.join(self.train_npy_dir, '{}-G1-{}'.format(self.name, Rc))
            if path.exists(prefix+'-Gs.npy') and Gs[n].shape == np.load(prefix+'-Gs.npy').shape:
                Gs[n] = np.load(prefix+'-Gs.npy')
                dGs[n] = np.load(prefix+'-dGs.npy')
            else:
                G, dG = self.__calc_G1(Rc)
                np.save(prefix+'-Gs.npy', G)
                np.save(prefix+'-dGs.npy', dG)
                Gs[n] = G
                dGs[n] = dG
            n += 1

            for eta in self.etas:
                for Rs in self.Rss:
                    prefix = path.join(self.train_npy_dir, '{}-G2-{}-{}-{}'.format(self.name, Rc, eta, Rs))
                    if path.exists(prefix+'-Gs.npy') and Gs[n].shape == np.load(prefix+'-Gs.npy').shape:
                        Gs[n] = np.load(prefix+'-Gs.npy')
                        dGs[n] = np.load(prefix+'-dGs.npy')
                    else:
                        G, dG = self.__calc_G2(Rc, eta, Rs)
                        np.save(prefix+'-Gs.npy', G)
                        np.save(prefix+'-dGs.npy', dG)
                        Gs[n] = G
                        dGs[n] = dG
                    n += 1

                for lam in self.lams:
                    for zeta in self.zetas:
                        prefix = path.join(self.train_npy_dir, '{}-G4-{}-{}-{}-{}'.format(self.name, Rc, eta, lam, zeta))
                        if path.exists(prefix+'-Gs.npy') and Gs[n].shape == np.load(prefix+'-Gs.npy').shape:
                            Gs[n] = np.load(prefix+'-Gs.npy')
                            dGs[n] = np.load(prefix+'-dGs.npy')
                        else:
                            G, dG = self.__calc_G4(Rc, eta, lam, zeta)
                            np.save(prefix+'-Gs.npy', G)
                            np.save(prefix+'-dGs.npy', dG)
                            Gs[n] = G
                            dGs[n] = dG
                        n += 1
        return Gs.transpose(1, 2, 0), dGs.transpose(1, 2, 3, 0)

    def load(self):
        loaded_G, loaded_dG = [], []
        for Rc in self.Rcs:
            prefix = path.join(self.train_npy_dir, '{}-G1-{}'.format(self.name, Rc))
            if path.exists(prefix+'-Gs.npy'):
                loaded_G.append(np.load(prefix+'-Gs.npy'))
                loaded_dG.append(np.load(prefix+'-dGs.npy'))

            for eta in self.etas:
                for Rs in self.Rss:
                    prefix = path.join(self.train_npy_dir, '{}-G2-{}-{}-{}'.format(self.name, Rc, eta, Rs))
                    if path.exists(prefix+'-Gs.npy'):
                        loaded_G.append(np.load(prefix+'-Gs.npy'))
                        loaded_dG.append(np.load(prefix+'-dGs.npy'))

                for lam in self.lams:
                    for zeta in self.zetas:
                        prefix = path.join(self.train_npy_dir, '{}-G4-{}-{}-{}-{}'.format(self.name, Rc, eta, lam, zeta))
                        if path.exists(prefix+'-Gs.npy'):
                            loaded_G.append(np.load(prefix+'-Gs.npy'))
                            loaded_dG.append(np.load(prefix+'-dGs.npy'))

        Gs = np.c_[loaded_G].transpose(1, 2, 0)
        dGs = np.c_[loaded_dG].transpose(1, 2, 3, 0)
        return Gs, dGs

    def __calc_G1(self, Rc):
        G, dG = np.empty((self.nsample, self.natom)), np.empty((self.nsample, self.natom, 3*self.natom))
        G_para, dG_para = np.zeros((self.nsample, self.natom)), np.zeros((self.nsample, self.natom, 3*self.natom))
        generator = self.__G1_generator(Rc)
        for m, G, dG in generator:
            G_para[m] = G
            dG_para[m] = dG
        self.comm.Allreduce(G_para, G, op=MPI.SUM)
        self.comm.Allreduce(dG_para, dG, op=MPI.SUM)
        return G, dG

    def __G1_generator(self, Rc):
        for m in range(self.min, self.max):
            atoms = self.atoms_objs[m]
            index, r, R, tanh, fc, cosine = self.__neighbour(m, atoms, Rc)
            dR = self.__deriv_R(m, index, r, R)
            G = np.empty((self.natom))
            dG = np.empty((self.natom, 3*self.natom))
            for i in range(self.natom):
                G[i] = np.sum(fc[i])
                dgi = - 3/Rc * (1 - tanh[i][:, None]**2) * tanh[i][:, None]**2 * dR[i]
                dG[i] = np.sum(dgi, axis=0)
            yield m, G, dG

    def __calc_G2(self, Rc, eta, Rs):
        G, dG = np.empty((self.nsample, self.natom)), np.empty((self.nsample, self.natom, 3*self.natom))
        G_para, dG_para = np.zeros((self.nsample, self.natom)), np.zeros((self.nsample, self.natom, 3*self.natom))
        generator = self.__G2_generator(Rc, eta, Rs)
        for m, G, dG in generator:
            G_para[m] = G
            dG_para[m] = dG
        self.comm.Allreduce(G_para, G, op=MPI.SUM)
        self.comm.Allreduce(dG_para, dG, op=MPI.SUM)
        return G, dG

    def __G2_generator(self, Rc, eta, Rs):
        for m in range(self.min, self.max):
            atoms = self.atoms_objs[m]
            index, r, R, tanh, fc, cosine = self.__neighbour(m, atoms, Rc)
            dR = self.__deriv_R(m, index, r, R)
            G = np.empty((self.natom))
            dG = np.empty((self.natom, 3*self.natom))
            for i in range(self.natom):
                gi = np.exp(- eta * (R[i] - Rs) ** 2) * fc[i]
                G[i] = np.sum(gi)
                dgi = gi[:, None] * ((-2*Rc*eta*(R[i][:, None]-Rs)*tanh[i][:, None] + 3*tanh[i][:, None]**2 - 3) / (Rc * tanh[i][:, None])) * dR[i]
                dG[i] = np.sum(dgi, axis=0)
            yield m, G, dG

    def __calc_G4(self, Rc, eta, lam, zeta):
        G, dG = np.empty((self.nsample, self.natom)), np.empty((self.nsample, self.natom, 3*self.natom))
        G_para, dG_para = np.zeros((self.nsample, self.natom)), np.zeros((self.nsample, self.natom, 3*self.natom))
        generator = self.__G4_generator(Rc, eta, lam, zeta)
        for m, G, dG in generator:
            G_para[m] = G
            dG_para[m] = dG
        self.comm.Allreduce(G_para, G, op=MPI.SUM)
        self.comm.Allreduce(dG_para, dG, op=MPI.SUM)
        return G, dG

    def __G4_generator(self, Rc, eta, lam, zeta):
        for m in range(self.min, self.max):
            atoms = self.atoms_objs[m]
            index, r, R, tanh, fc, cosine = self.__neighbour(m, atoms, Rc)
            dR = self.__deriv_R(m, index, r, R)
            dcos = self.__deriv_cosine(m, index, r, R, cosine)
            G = np.empty((self.natom))
            dG = np.empty((self.natom, 3*self.natom))
            for i in range(self.natom):
                angular = (1+lam*cosine[i])
                common = (2**(1-zeta)) * (angular**(zeta-1)) * np.exp(-eta*(R[i][:, None]**2+R[i][None, :]**2)) * fc[i][:, None] * fc[i][None, :]
                gi = common * angular
                filter = np.identity(len(index[i]), dtype=bool)
                gi[filter] = 0.0
                G[i] = np.sum(gi)
                dgi_R = ((-2*Rc*eta*R[i][:, None]*tanh[i][:, None] + 3*tanh[i][:, None]**2 - 3) / (Rc * tanh[i][:, None])) * dR[i]
                dgi_cos = zeta * lam * dcos[i]
                dgi = common[:, :, None] * (angular[:, :, None] * (dgi_R[None, :, :] + dgi_R[:, None, :]) + dgi_cos)
                filter = filter[:, :, None].repeat(3*self.natom, axis=2)
                dgi[filter] = 0.0
                dG[i] = np.sum(dgi, axis=(0, 1))
            yield m, G, dG

    def memorize(f):
        if f.__name__ == '__neighbour':
            cache = {}

            def helper(self, m, atoms, Rc):
                if (m, Rc) not in cache:
                    cache[(m, Rc)] = f(self, m, atoms, Rc)
                return cache[(m, Rc)]
            return helper
        elif f.__name__ == '__deriv_R':
            cache = {}

            def helper(self, m, index, r, R):
                if m not in cache:
                    cache[m] = f(self, m, index, r, R)
                return cache[m]
            return helper
        elif f.__name__ == '__deriv_cosine':
            cache = {}

            def helper(self, m, index, r, R, cosine):
                if m not in cache:
                    cache[m] = f(self, m, index, r, R, cosine)
                return cache[m]
            return helper

    @memorize
    def __neighbour(self, m, atoms, Rc):
        atoms.set_cutoff(Rc)
        atoms.calc_connect()
        index = [atoms.connect.get_neighbours(i)[0] - 1 for i in frange(self.natom)]
        r, R, fc, tanh = self.__distance_ij(atoms, Rc)
        cosine = self.__cosine_ijk(atoms, Rc)

        return index, r, R, fc, tanh, cosine

    def __distance_ij(self, atoms, Rc):
        r, R, fc, tanh = [], [], [], []
        for i in frange(self.natom):
            ri, Ri = [], []
            for n in frange(atoms.n_neighbours(i)):
                dist = farray(0.0)
                diff = fzeros(3)
                atoms.neighbour(i, n, distance=dist, diff=diff)
                ri.append(diff)
                Ri.append(dist)
            r.append(np.array(ri))
            R.append(np.array(Ri))
            fc.append(np.tanh(1-R[i-1]/Rc)**3)
            tanh.append(np.tanh(1-R[i-1]/Rc))
        return r, R, fc, tanh

    def __cosine_ijk(self, atoms, Rc):
        cosine = []
        for i in frange(self.natom):
            n_neighb = atoms.n_neighbours(i)
            cosi = np.zeros((n_neighb, n_neighb))
            for j in frange(n_neighb):
                for k in frange(n_neighb):
                    if k == j:
                        pass
                    else:
                        cosi[j-1][k-1] = atoms.cosine_neighbour(i, j, k)
            cosine.append(cosi)
        return cosine

    @memorize
    def __deriv_R(self, m, index, r, R):
        dR = []
        for i in range(self.natom):
            n_neighb = len(R[i])
            dRi = np.zeros((n_neighb, 3*self.natom))
            for j in index[i]:
                for l in range(self.natom):
                    if l == i:
                        for alpha in range(3):
                            dRi[j][3*l+alpha] = - r[i][j][alpha] / R[i][j]
                    elif l == j:
                        for alpha in range(3):
                            dRi[j][3*l+alpha] = + r[i][j][alpha] / R[i][j]
            dR.append(dRi)
        return dR

    @memorize
    def __deriv_cosine(self, m, index, r, R, cosine):
        dcos = []
        for i in range(self.natom):
            n_neighb = len(R[i])
            dcosi = np.zeros((n_neighb, n_neighb, 3*self.natom))
            for j in index[i]:
                for k in index[i]:
                    for l in range(self.natom):
                        if l == i:
                            for alpha in range(3):
                                dcosi[j][k][3*l+alpha] = (+ r[i][j][alpha] / R[i][j]**2) * cosine[i][j][k] + \
                                                         (+ r[i][k][alpha] / R[i][k]**2) * cosine[i][j][k] + \
                                                         (- (r[i][j][alpha] + r[i][k][alpha])) / (R[i][j] * R[i][k])
                        elif l == j:
                            for alpha in range(3):
                                dcosi[j][k][3*l+alpha] = (- r[i][j][alpha] / R[i][j]**2) * cosine[i][j][k] + \
                                                         (+ r[i][k][alpha]) / (R[i][j] * R[i][k])
                        elif l == k:
                            for alpha in range(3):
                                dcosi[j][k][3*l+alpha] = (- r[i][k][alpha] / R[i][k]**2) * cosine[i][j][k] + \
                                                         (+ r[i][j][alpha]) / (R[i][j] * R[i][k])
            dcos.append(dcosi)
        return dcos


class SFGenerator(InputGenerator):
    pass


def make_dataset(allcomm, allrank, allsize):
    train_dir = 'training_data'
    train_xyz_file = path.join(train_dir, 'xyz', other.xyzfile)
    train_npy_dir = path.join(train_dir, 'npy', other.name)
    if not path.exists(train_npy_dir):
        mkdir(train_npy_dir)
    label = LabelGenerator(train_npy_dir, other.name)
    input = InputGenerator(train_npy_dir, other.name, hp.Rcs, hp.etas, hp.Rss, hp.lams, hp.zetas)

    if bool.CALC_INPUT:
        alldataset = AtomsReader(train_xyz_file)
        coordinates = []
        for data in alldataset:
            if data.config_type == other.name and data.cohesive_energy < 0.0:
                coordinates.append(data)
        nsample = len(coordinates)
        Es, Fs = label.make(coordinates, hp.natom, nsample)
        ninput = len(hp.Rcs) + \
            len(hp.Rcs)*len(hp.etas)*len(hp.Rss) + \
            len(hp.Rcs)*len(hp.etas)*len(hp.lams)*len(hp.zetas)
        Gs, dGs = input.make(allcomm, allsize, allrank, coordinates, hp.natom, nsample, ninput)
    else:
        Es, Fs = label.load()
        Gs, dGs = input.load()
        nsample = len(Es)
        ninput = len(Gs[0][0])

    dataset = [[Es[i], Fs[i], Gs[i], dGs[i]] for i in range(nsample)]
    return dataset, nsample, ninput


def main():
    allcomm = MPI.COMM_WORLD
    allrank = allcomm.Get_rank()
    allsize = allcomm.Get_size()
    make_dataset(allcomm, allrank, allsize)


if __name__ == '__main__':
    main()
