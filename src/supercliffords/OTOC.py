import stim
import numpy as np
import supercliffords.gates as gates
import supercliffords.entropy as entropy
import time
import matplotlib.pyplot as plt
import random

"""
The code in this file allows one to compute the OTOC of certain random circuits. 

The function row_sum and g are taken directly from [arXiv:quant-ph/0406196].
"""




def REF_binary(A, signs, N):
    """
    - Purpose: Given a N x N matrix, A and an array of signs. This will convert the matrix to row echelon form (REF) and convert the signs using the rowsum operation.
    - Inputs: 
            - A (binary N x N matrix).
            - signs (array of length N)
            - N (integer).
    - Outputs: 
            - A (binary N x N matrix - in REF).
            - signs (array of length N - updated using rowsum operation).

    """
    
    n_rows, n_cols = A.shape

    # Compute row echelon form (REF)
    current_row = 0
    for j in range(n_cols):  # For each column
        if current_row >= n_rows:
            break
            
        pivot_row = current_row
     
        # find the first row in this column with non-zero entry. 
        # this becomes the pivot row
        while pivot_row < n_rows and A[pivot_row, j] == 0:
            pivot_row += 1
        
        # if we reach the end, this column cannot be eliminated. 
        if pivot_row == n_rows:
            continue  
            
        # otherwise, swap current row with the pivot row
        A[[current_row, pivot_row]] = A[[pivot_row, current_row]]
        a = signs[current_row]
        signs[current_row] = signs[pivot_row]
        signs[pivot_row] = a
        

        pivot_row = current_row
        current_row += 1
        
        # Eliminate rows below
        for i in range(current_row, n_rows):
            # subtract current row from any other rows beneath with 
            # a non-zero entry in this current column 
            if A[i, j] == 1:
                A[i] = (A[i] +  A[pivot_row]) % 2 # subtracting is same as adding in GF(2)
                signs[i] = row_sum(A[i], A[pivot_row], signs[i], signs[pivot_row], N)
                             
    return A, signs


def g(x1, z1, x2, z2):
    """
    Purpose: Computes the function g needed for the rowsum operation.
    Inputs:
         - x1, z1, x2, z2  in {0, 1} (i.e. four bits).
    Outputs:
         - rh in {0, 1} (i.e. one bit).
    """


    if (x1 ==0) and (z1 == 0):
        g = 0
    if (x1 == 0) and (z1 == 1):
        g = x2*(1 - 2*z2)
    if (x1 == 1) and (z1 == 0):
        g = z2*(2*x2 -1)
    if (x1 == 1) and (z1 == 1):
        g = z2 - x2
        
    return g    


def row_sum(h, i, rh, ri, N):
    """ 
    Purpose: Compute the row_sum operation.
    Inputs:
         - h, i -  two arrays of bits, length N (two rows from a binary matrix).
         - rh, ri - two bits (the signs corresponding to the rows, h, i).
         - N - an integer. The length of the arrays.
    Outputs:
         - rh - a bit. The sign of the new row obtained from adding h + i as bitstrings.
    """

    m = np.size(h)

    k = 0
    for j in range(N):
        k += g(i[j], i[j+N], h[j], h[j+N])

    f = 2*rh +2*ri + k
    
    if (f % 4) == 0:
        rh = 0
    else:
        rh = 1
        
    return rh    


    

def xs(binMat):
    """
    Purpose: Given a stabilizer tableau (N, 2N) extract the X's of the tableau (i.e. the first N columns).
    Inputs:
         - binMat - a stabilizer tableau ( i.e. an (N, 2N) binary matrix).
    Outputs:
         - xs - a binary matrix of size (N, N).

    """

    N = len(binMat)
    xs = np.zeros((N, N))
    xs[:,:] = binMat[:, :N]

    return xs


def small_zs(binMat, size2, N):
    """
    Purpose: Given a stabilizer tableau (N, 2N), extract a small portion of the Z's. I.e. the second N columns and only the rows with index larger than size2.
    Inputs:
          - binMat - a (N, 2N) binary matrix.
          - size2 - an integer, less than N.
          - N - an integer, dimension of binMat.
    Outputs:
          - small_zs - a (N-size2, N) binary matrix.

    """

    small_zs = np.zeros((size2, N))
    small_zs[:,:] = binMat[N-size2:, N:]
    return small_zs


def OTOC_FS3_Np(N, T, rep, res, slow, Op):
    """
        - Purpose: Run a fast scrambling circuit and use it to compute an OTOC. Each time step this circuit acts on N/slow qubits. On the qubits which it acts on, it applies Z.H on 1/4 of the qubits and C3 on the remaing ones. In order to compute the OTOC one needs to introduce another operator, this is given by Op.

        - Inputs: 
               - N: integer (number of qubits).
               - T: integer (number of timesteps).
               - rep: integer (number of repetitions).
               - res: integer (resolution - i.e. how often the OTOC gets computed).
               - slow: integer (determines how much we slow down the action of the circuit).
               - Op: stim.TableauSimulator (gives a new operator which should be a super-Clifford and which we will use for computing the OTOC
        - Outputs: 
               - v - an array of real numbers of length T/res containing the values of the OTOC at different timesteps.
               - w - an array of real numbers of length T/res containing the timesteps.

"""
    Size = int(T/res) #specify size of output vectors.
    v = np.zeros(Size)
    w = np.zeros(Size)
    for m in range(Size):
        w[m] = m*res

    for k in range(0, rep):
        s = stim.TableauSimulator()
        for i in range(0, T):
            if i == 0:
                s = gates.Id_Step(N, s) #To give correct initial value.
            else:     
                s = gates.FS3_NpStep(N, s, slow) #evolution of circuit.
                
            if (i % res) == 0:
                tableau1: stim.Tableau = s.current_inverse_tableau()**-1
                n1 = len(tableau1)
                tableau2: stim.Tableau = Op.current_inverse_tableau()**-1
                n2 = len(tableau2)
                tableau3: stim.Tableau = s.current_inverse_tableau()
                tableau_tot: stim.Tableau = (tableau3*tableau2)*tableau1
                n = len(tableau_tot)
                zs = [tableau_tot.z_output(k) for k in range(n)]
                zs2 = np.array(zs)
                signs = [(zs[k].sign).real for k in range(n)]
                signs2 = np.array(signs)
                bMat = entropy.binary_matrix(zs2)
            
                signs3 = entropy.convert_signs(signs2)
               
                REF, signs3 = REF_binary(bMat, signs3, N)
            

                
                xs1 = xs(REF)
                rows = entropy.rows(xs1)
                rank = entropy.gf2_rank(rows)
                size2 = N - rank
            

                small = small_zs(REF, size2, N)

                REF2 = small #RREF_binary(small)
                shape = np.shape(REF2)

                signs4 = signs3[rank:]
                Ans = 0

                for k in range(size2):
                    if (signs4[k] == 1):
                          Ans = 1

                        
                if (Ans == 1):
                    v[int(i/res)] += 0 
                else:    
                    v[int(i/res)] +=(2**(-(rank)/2))/rep        
                    
    return v, w           



def OTOC_Rand1(N, T, rep, res, Op):
    """
        - Purpose: Run a slow scrambling O(1) circuit with local interactions and use it to compute an OTOC. Each time step this circuit acts on 3 qubits. On the first qubit it acts with Z.H and then it acts with C3 on the three qubits, randomizing which qubit is control. In order to compute the OTOC one needs to introduce another operator, this is given by Op.

        - Inputs: 
               - N: integer (number of qubits).
               - T: integer (number of timesteps).
               - rep: integer (number of repetitions).
               - res: integer (resolution - i.e. how often the OTOC gets computed).
               - Op: stim.TableauSimulator (gives a new operator which should be a super-Clifford and which we will use for computing the OTOC
        - Outputs: 
               - v - an array of real numbers of length T/res containing the values of the OTOC at different timesteps.
               - w - an array of real numbers of length T/res containing the timesteps.

"""
    Size = int(T/res) #specify size of output vectors.
    v = np.zeros(Size)
    w = np.zeros(Size)
    for m in range(Size):
        w[m] = m*res

    for k in range(0, rep):
        s = stim.TableauSimulator()
        for i in range(0, T):
            if i == 0:
                s = gates.Id_Step(N, s)
            else:
                s = gates.Rand1Step(N, s)
            if (i % res) == 0:
                tableau1: stim.Tableau = s.current_inverse_tableau()**-1
                n1 = len(tableau1)
                tableau2: stim.Tableau = Op.current_inverse_tableau()**-1
                n2 = len(tableau2)
                tableau3: stim.Tableau = s.current_inverse_tableau()
                tableau_tot: stim.Tableau = (tableau3*tableau2)*tableau1
                n = len(tableau_tot)
                zs = [tableau_tot.z_output(k) for k in range(n)]
                zs2 = np.array(zs)
                signs = [(zs[k].sign).real for k in range(n)]
                signs2 = np.array(signs)
                bMat = entropy.binary_matrix(zs2)
            
                signs3 = entropy.convert_signs(signs2)
               
                REF, signs3 = REF_binary(bMat, signs3, N)
            

                
                xs1 = xs(REF)
                rows = entropy.rows(xs1)
                rank = entropy.gf2_rank(rows)
                size2 = N - rank
            

                small = small_zs(REF, size2, N)

                REF2 = small #RREF_binary(small)
                shape = np.shape(REF2)

                signs4 = signs3[rank:]
                Ans = 0

                for k in range(size2):
                    if (signs4[k] == 1):
                          Ans = 1

                        
                if (Ans == 1):
                    v[int(i/res)] += 0
                else:    
                    v[int(i/res)] +=(2**(-(rank)/2))/rep        
                    
    return v, w    



def OTOC_LocInt(N, T, rep, res, slow, Op):
    """
        - Purpose: Run a slow scrambling O(N) circuit with local interactions and use it to compute an OTOC. Each time step this circuit acts on N/slow qubits. On even time steps it acts on N/slow qubits with Z.H on odd timesteps it acts on N/slow qubits with C3 (randomizing which qubit is control) - but the C3 gate is constrained to be local i.e. nearest neighbour. For simplicity, we will go two timesteps at a time. 

        - Inputs: 
               - N: integer (number of qubits).
               - T: integer (number of timesteps).
               - rep: integer (number of repetitions).
               - res: integer (resolution - i.e. how often the OTOC gets computed).
               - Op: stim.TableauSimulator (gives a new operator which should be a super-Clifford and which we will use for computing the OTOC
        - Outputs: 
               - v - an array of real numbers of length T/res containing the values of the OTOC at different timesteps.
               - w - an array of real numbers of length T/res containing the timesteps.
"""
    
    Size = int(T/res) #specify size of output vectors.
    v = np.zeros(Size)
    w = np.zeros(Size)
    for m in range(Size):
        w[m] = m*res

    for k in range(0, rep):
        s = stim.TableauSimulator()
        for i in range(0, T):
            if i == 0:
                s = gates.Id_Step(N, s)
            else:
                s = gates.LocInt_Step1(N, s, slow)
                s = gates.LocInt_Step2(N, s, slow)


            if i % 2 == 0:
                s = gates.LocInt_Step3(N, s, slow)

            else:
                s = gates.LocInt_Step4(N, s, slow)
                
            if (i % res) == 0:
                tableau1: stim.Tableau = s.current_inverse_tableau()**-1
                n1 = len(tableau1)
                tableau2: stim.Tableau = Op.current_inverse_tableau()**-1
                n2 = len(tableau2)
                tableau3: stim.Tableau = s.current_inverse_tableau()
                tableau_tot: stim.Tableau = (tableau3*tableau2)*tableau1
                n = len(tableau_tot)
                zs = [tableau_tot.z_output(k) for k in range(n)]
                zs2 = np.array(zs)
                signs = [(zs[k].sign).real for k in range(n)]
                signs2 = np.array(signs)
                bMat = entropy.binary_matrix(zs2)
            
                signs3 = entropy.convert_signs(signs2)
               
                REF, signs3 = REF_binary(bMat, signs3, N)
            

                
                xs1 = xs(REF)
                rows = entropy.rows(xs1)
                rank = entropy.gf2_rank(rows)
                size2 = N - rank
            

                small = small_zs(REF, size2, N)

                REF2 = small #RREF_binary(small)
                shape = np.shape(REF2)

                signs4 = signs3[rank:]
                Ans = 0

                for k in range(size2):
                    if (signs4[k] == 1):
                          Ans = 1

                        
                if (Ans == 1):
                    v[int(i/res)] += 0
                else:    
                    v[int(i/res)] +=(2**(-(rank)/2))/rep        
                    
    return v, w    


def Op(N):
    """
    Purpose: build a stabilizer tableau corresponding to an operator that will act as the perturbation V(0) in the calculation of the OTOC.
    Inputs:
          - N - an integer (the number of qubits in the chain).
    Outputs:
         - s - a stim.TableauSimulator() with the gate(s) corresponding the operator V(0).
    """
    s = stim.TableauSimulator()

    c1 = stim.Circuit()

    c = stim.Circuit()
    r = random.randint(0, N-3)
    c.append_operation("I", [N-1])
    c.append_operation("I", [0])
    s.do(c)
    s.do(gates.ZH(r+1))
    s.do(gates.ZH(r+2))
    s.do(gates.C3(r, r+1, r+2))

    return s

    

def main():
    """
     Below one can evaluate the OTOC for one of three possible circuits. Rand1 is a nearest neighbour circuit, that acts on O(1) qubits at each timestep. LocInt is a nearest neighbour circuit that acts on O(N) qubits at each timestep. FS3_Np is an all-to-all circuit that acts on O(N) qubits at each timestep. In order to run this one needs to specify the following:
    - N - an integer, the number of qubits in the chain.
    - T - an integer, the number of timesteps for the evolution.
    - rep - the number of repititons to smooth out fluctuations.
    - res - the resolution, that specifies how often to calculate the OTOC.
    - slow - the proportion of the qubits to act on at each timestep.
    - Op1 -the operator that will be V(0) in the calculation of the OTOC. This can be modified by changing the function Op(N), above.

    """


    
    startTime = time.time()


    N = 120 
    T = 100
    rep = 10
    res = 1
    slow = 2
    Op1 = Op(N)
    v1, w1 = OTOC_LocInt(N, T, rep, res, slow, Op1)
#    v2, w2 = OTOC_Rand1(N, T, rep, res, Op1)
#    v3, w3 = OTOC_FS3_Np(N, T, rep, res, slow, Op1)

    
        


    totTime = (time.time() - startTime)
    print('Execution time in seconds:' + str(totTime))
    


            	      
    plt.plot(w1, v1)
    plt.xlabel('Time')
    plt.ylabel('OTOC')
    plt.title(f'OTOC for N = {N}')
    plt.show()  
    


    



if (__name__ == '__main__'):
    main()     
 
        
