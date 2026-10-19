# Verbatim definitions from upstream commit eaec7012a1928c36e73ffcf7ec894c5e3e28bfe3.
def dendogram(i:data, region:rows=None, stop=None, before=None, lvl = 0):
  region = region or i.rows
  stop = stop or 4
  node = o(this="dendogram",here=clone(i,region),
           reference=None, enough=0,
           left=None,right=None)
  if lvl < stop:
    lefts,rights,left,right  = half(i,region, False, before)
    node.enough = dists(i,right,rights[0])
    node.reference=right
    node.left=dendogram(i,lefts, stop, left, lvl+1)
    node.right=dendogram(i,rights,stop, right, lvl+1) 
  return node

def leafs(node, lvl = 0, centroids = []):
    if not (node.left or node.right): centroids.append(random.choice(node.here.rows))
    if node.left: leafs(node.left, lvl+1, centroids)
    if node.right: leafs(node.right, lvl+1, centroids)
    return centroids
