# Verbatim definitions from upstream commit eaec7012a1928c36e73ffcf7ec894c5e3e28bfe3.
def warm_smo_plus(args, score = lambda B,R,I,N : B-R, method = 'LLM', start = 'Random'):
    def _ranked(lst:rows) -> rows:
        "Sort `lst` by distance to heaven. Called by `_smo1()`."
        lst = sorted(lst, key = lambda r:d2h(i,r))
        return lst

    
    if start == 'Random':
        i = DATA(csv(args.dataset))
        random.shuffle(i.rows)

        k = int(args.last * 0.6)
        rem = args.last - k

        points = random.choices(i.rows, k = k)
        sorted(points, key = lambda p : chebyshev(i,p))

        best_points = points[:k/2]
        rest_points = points[k/2:]

        #done, new_done ,todo = WARM_FEW_API(i, args, method = method)
        all = []
        k = 0
        while k  < rem:
            done = random.choices(best_points, k = 2) + random.choices(rest_points, k= 2)
            done = set((tuple(_) for _ in done))
            todo = set((tuple(_) for _ in i.rows)) - done


            done, new_done, todo = WARM_FEW_API(i, args,  list(todo), list(done), method = method)

            all += done + new_done
            k += 1


        # all = []
        # k = 0
        # while k < 20:
        #     done = random.choices(i.rows, k=4)
        #     done = set((tuple(_) for _ in done))
        #     todo = set((tuple(_) for _ in i.rows)) - done

        #     done, new_done, todo = WARM_FEW_API(i, args,  list(todo), list(done), method = method)
        #     print("best of new done",chebyshev(i, new_done[0]))
        #     all += done + new_done
        #     k += 2


         

    elif start == 'Diversity':
        i = DATA(csv(args.dataset))
        random.shuffle(i.rows)

        d = dendogram(i,stop = 4)
        points = leafs(d,centroids=[])
        
        points = sorted(points, key = lambda p : chebyshev(i,p))

        # X = np.array(i.rows)
        

        # kmeans = KMeans(n_clusters=10,  n_init=10)
        # clusters = kmeans.fit_predict(X)

        # centroids = kmeans.cluster_centers_
        # points = centroid_rows = np.array([X[np.argmin(np.linalg.norm(X - centroid, axis=1))] for centroid in centroids])
        

        # points = sorted(points, key = lambda p : chebyshev(i,p))
        # for p in points:
        #     print(chebyshev(i,p))
        best_points = points[:len(points)//2]
        rest_points = points[len(points)//2:]

        


        #print("best of points", chebyshev(i,best_points[0]))

        #done, new_done ,todo = WARM_FEW_API(i, args, method = method)
        all = []
        k = 0
        while k  < 30:
            done = random.choices(best_points, k = 2) + random.choices(rest_points, k= 2)
            done = set((tuple(_) for _ in done))
            todo = set((tuple(_) for _ in i.rows)) - done


            done, new_done, todo = WARM_FEW_API(i, args,  list(todo), list(done), method = method)
            #print("best of new done",chebyshev(i, new_done[0]))


            all += done + new_done
            k += 2

        # i = DATA(csv(args.dataset))
        # random.shuffle(i.rows)
        # random.shuffle(i.rows)
        # best, rest, n = branch(i, i.rows, 15)


        # temp_best = random.choices(best, k=4)
        # temp_rest = random.choices(rest, k=4)

        # done = sorted(temp_best + temp_rest, key=lambda p: chebyshev(i, p))
        # print("best of intial", chebyshev(i,done[0]))
        # done = set(tuple(_) for _ in done)
        # todo = set(tuple(_) for _ in i.rows) - done
        # all = []

        # done = list(done)
        # todo = list(todo)

        # #print("best of points", chebyshev(i,best_points[0]))

        # #done, new_done ,todo = WARM_FEW_API(i, args, method = method)
        # all = []
        # k = 0
        # while k  < 28:
        #     # done = random.choices(best_points, k = 2) + random.choices(rest_points, k= 2)
        #     # done = set((tuple(_) for _ in done))
        #     # todo = set((tuple(_) for _ in i.rows)) - done


        #     done, new_done, todo = WARM_FEW_API(i, args,  list(todo), list(done), method = method)
        #     print("best of new done",chebyshev(i, new_done[0]))


        #     all += done + new_done
        #     k += 2
        
    elif start == 'Surrogate':
        besties = lambda B, R: B - R
        resties = lambda B, R: R - B

        i = DATA(csv(args.dataset))

        random.shuffle(i.rows)
        best, rest, n = branch(i, i.rows, 8)
        print("rest",len(rest))
        print("best", len(best))


        temp_best = random.choices(best, k=4)
        temp_rest = random.choices(rest, k=4)

        done = sorted(temp_best + temp_rest, key=lambda p: chebyshev(i, p))

        #print("best of intial", chebyshev(i,done[0]))
        done = set(tuple(_) for _ in done)
        todo = set(tuple(_) for _ in i.rows) - done
        all = []

        done = list(done)
        todo = list(todo)
        k = 0
        while k < 44:
            cut = int(.5 + len(done) ** 0.5)
            done = sorted(done, key=lambda p: chebyshev(i, p))
            best = clone(i, done[:cut])
            rest = clone(i, done[cut:])
            
            new_best = []
            score = besties
            key = lambda r: score(loglikes(best, r, len(done), 2),
                                loglikes(rest, r, len(done), 2))

            random.shuffle(todo)  # optimization: only sort a random subset of todo 
            todo = sorted(todo[:100], key=key, reverse=True) + todo[100:]
            new_best.append(todo[0])

            random.shuffle(todo)  # optimization: only sort a random subset of todo 
            todo = sorted(todo[:100], key=key, reverse=True) + todo[100:]
            new_best.append(todo[0])



            score = resties
            new_rest = []
            key = lambda r: score(loglikes(best, r, len(done), 2),
                                loglikes(rest, r, len(done), 2))

            random.shuffle(todo)  # optimization: only sort a random subset of todo 
            todo = sorted(todo[:100], key=key, reverse=True) + todo[100:]
            new_rest.append(todo[0])
            random.shuffle(todo)  # optimization: only sort a random subset of todo 
            todo = sorted(todo[:100], key=key, reverse=True) + todo[100:]
            new_rest.append(todo[0])

            # for _ in new_best + new_rest:
            #     print("chebyshev of points", chebyshev(i,_))
           

            done, new_done, todo = WARM_FEW_API(i, args, todo, sorted(new_best + new_rest, key = lambda p : chebyshev(i,p)), method=method, iscombined=False)
            # if new_done:
            #     print("extra best",chebyshev(i,new_done[0]))
            # done += new_done  # Add new_done rows to done
            # todo = [row for row in todo if row not in new_done]  # Remove new_done from todo

            all += new_done
            k += 2


    return _ranked(all)
