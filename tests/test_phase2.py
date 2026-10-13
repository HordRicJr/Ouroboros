import numpy as np
from univers.ecology import _diffuse
from univers.engine import Universe
from univers.genetics import NT, make_child, make_genome, phenotype
from univers.persistence import MemoryStore
from univers.rng import Rng


def test_child_alleles_come_from_parents_without_mutation():
    g = np.random.default_rng(1)
    a = make_genome(np.full(NT, 0.2), g, 0.05)
    b = make_genome(np.full(NT, 0.8), g, 0.05)
    c = make_child(a, b, g, mutation_rate=0.0)
    for t in range(NT):
        assert c[0, t] in a[:, t] and c[1, t] in b[:, t]


def test_mutation_changes_genome_and_stays_in_bounds():
    g = np.random.default_rng(2)
    a = make_genome(np.full(NT, 0.5), g)
    c = make_child(a, a, g, mutation_rate=1.0)
    assert (c >= 0).all() and (c <= 1).all()
    assert not np.allclose(phenotype(c), phenotype(a))


def test_dispersal_conserves_mass():
    land = np.ones((10, 10), bool)
    land[:, 5] = False
    x = np.zeros((1, 3, 10, 10))
    x[0, :, 2, 2] = 10.0
    x *= land
    y = x
    for _ in range(20):
        y = _diffuse(y, np.full((1, 1, 10, 10), 0.3), land)
    assert abs(y.sum() - x.sum()) < 1e-9
    assert (y[..., ~land] == 0).all()


def test_genesis_ecosystem():
    u = Universe("g", 3)
    kinds = {s.kind for s in u.eco.species}
    assert kinds == {"plant", "herbivore", "predator", "human"}
    assert (u.eco.totals() > 0).all()
    assert len(u.people.alive_persons()) == 24  # 3 campements x 4 couples


def test_speciation_and_extinction():
    u = Universe("s", 4)
    e = u.eco
    herb = [s.id for s in e.species if s.kind == "herbivore"][0]
    # peuplement dense en deux régions dont l'une diverge fortement
    e.N[herb] = 0.0
    land = u.world.is_land
    cells = np.argwhere(land)[:80]
    for k, (y, x) in enumerate(cells):
        e.N[herb, :, y, x] = 5.0
        if k >= 40:
            e.T[herb, :, y, x] = np.clip(e.T[herb, :, y, x] + 0.4, 0, 1)
    n_before = len(e.species)
    ev = e._speciation(u.world, Rng(4), 100)
    assert len(e.species) == n_before + 1 and ev[0].type == "speciation"
    assert e.species[-1].parent_id == herb
    assert e.N.shape[0] == e.T.shape[0] == len(e.species)
    # extinction
    e.N[herb] = 0.0
    ev = e._extinctions(200)
    assert any(x.type == "extinction" and x.payload["species_id"] == herb for x in ev)
    assert e.species[herb].extinct_tick == 200


def test_lineage_kinship_and_genealogy():
    u = Universe("l", 5)
    u.step(3 * 365)
    pp = u.people
    kids = [p for p in pp.persons.values() if p.mother_id is not None]
    assert kids, "des naissances auraient dû avoir lieu en 3 ans"
    k = kids[0]
    mother, father = pp.persons[k.mother_id], pp.persons[k.father_id]
    assert k.id in mother.children_ids and k.id in father.children_ids
    assert pp.are_kin(k.id, mother.id, 2) and pp.are_kin(k.id, father.id, 1)
    founders = [p for p in pp.persons.values() if p.mother_id is None]
    assert not pp.are_kin(founders[0].id, founders[-1].id, 2)
    tree = pp.genealogy(mother.id, 2, 2)
    assert any(c["id"] == k.id for c in tree["descendants"]["children"])
    # génome enfant : phénotype entre ceux des parents (±mutation)
    cg = phenotype(k.genome_array())
    assert np.all(np.abs(cg - phenotype(mother.genome_array())) < 0.5)


def test_full_resume_identical_with_eco_and_people():
    u = Universe("r", 8, start_year=2015)
    u.step(120)
    store = MemoryStore()
    store.save(u)
    r = store.load("r")
    assert np.array_equal(u.eco.N, r.eco.N) and len(u.people.persons) == len(r.people.persons)
    e1, e2 = u.step(200), r.step(200)
    assert [e.to_dict() for e in e1] == [e.to_dict() for e in e2]
    assert np.array_equal(u.eco.N, r.eco.N) and np.array_equal(u.eco.T, r.eco.T)
    assert u.people.to_dict() == r.people.to_dict()
