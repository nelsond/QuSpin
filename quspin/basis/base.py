from __future__ import print_function
import numpy as _np
import scipy.sparse as _sp
import warnings


MAXPRINT = 50
# this file stores the base class for all basis classes

__all__=["basis","isbasis"]

class basis(object):


	def __init__(self):
		self._Ns = 0
		self._basis = _np.asarray([])
		self._operators = "no operators for base."
		self._unique_me = True
		self._check_symm = None
		self._check_pcon = None
		if self.__class__.__name__ == 'basis':
			raise ValueError("This class is not intended"
							 " to be instantiated directly.")


	def __str__(self):
		
		string = "reference states: \n"
		if self._Ns == 0:
			return string
		
		str_list = list(self._get__str__())
		if self._Ns > MAXPRINT:
			try:
				i1 = list(str_list[-1]).index("|")
				i2 = list(str_list[-1]).index(">",-1)
				l = (i1+i2)//2 + (1-(i1+i2)%2)
			except:
				l = len(str_list[-1])//2

			t = (" ".join(["" for i in range(l)]))+":"
			str_list.insert(MAXPRINT//2,t)
		
		string += "\n".join(str_list)
		string += "\nsee review arXiv:1101.3281 for more details about reference states for symmetry reduced blocks.\n"
		return string

	@property
	def Ns(self):
		"""int: number of states in the Hilbert space."""
		return self._Ns

	@property
	def operators(self):
		"""set: set of availible operator strings."""
		return self._operators

	@property
	def N(self):
		"""int: number of sites the basis is constructed with."""
		return self._N

	@property
	def blocks(self):
		"""dict: contains the quantum numbers (blocks) for the symmetry sectors."""
		return dict(self._blocks)

	@property
	def sps(self):
		"""int: number of local degrees of freedom."""
		try:
			return self._sps
		except AttributeError:
			raise NotImplementedError("basis class: {0} missing local number of degrees of freedom per site 'sps' required for entanglement entropy calculations!".format(self.__class__))

	def _Op(self,opstr,indx,J,dtype):
		raise NotImplementedError("basis class: {0} missing implementation of '_Op' required for calculating matrix elements!".format(self.__class__))	

	def inplace_Op(self,v_in,opstr,indx,J,dtype,transposed=False,conjugated=False,v_out=None):
		"""Calculates the action of an operator on a state.

		Parameters
		-----------
		v_in : array_like
			state (or states stored in columns) to act on with the operator.
		opstr : str
			Operator string in the lattice basis format. For instance:
			>>> opstr = "zz"
		indx : list(int)
			List of integers to designate the sites the lattice basis operator is defined on. For instance:
			>>> indx = [2,3]
		J : scalar
			Coupling strength.
		dtype : 'type'
			Data type (e.g. numpy.float64) to construct the operator with.
		transposed : bool, optional
			if True this function will act with the trasposed operator.
		conjugated : bool, optional
			if True this function will act with the conjugated operator.
		v_out : array_like
			output array, must be the same shape as `v_in` aand matching type of the output.

		Returns
		--------
		numpy.ndarray
			* if v_out is not None, this function modifies v_out inplace and returns it. 

			
		Examples
		--------

		>>> J = 1.41
		>>> indx = [2,3]
		>>> opstr = "zz"
		>>> dtype = np.float64
		>>> ME, row, col = Op(opstr,indx,J,dtype)

		"""

		if v_in.__class__ not in [_np.ndarray, _np.matrix]:
			v_in = _np.asanyarray(v_in)

		if v_in.shape[0] != self.Ns:
			raise ValueError("dimension mismatch")

		if v_out is None:
			result_dtype = _np.result_type(v_in.dtype,dtype)
			v_out = _np.zeros_like(v_in,dtype=result_dtype)
		else:
			if v_out.__class__ not in [_np.ndarray, _np.matrix]:
				v_out = _np.asanyarray(v_out)

			if v_out.shape != v_in.shape:
				raise ValueError("v_in.shape != v_out.shape")



		if not transposed:
			ME, row, col = self.Op(opstr, indx, J, dtype)
		else:
			ME, col, row = self.Op(opstr, indx, J, dtype)

		if conjugated:
			ME = ME.conj()

		# TODO: implement these in low level language.
		if self._unique_me:
			v_out[row] += _np.multiply(v_in[col].T,ME).T
		else:
			while len(row) > 0:
				# if there are multiply matrix elements per row as there are for some
				# symmetries availible then do the indexing for unique elements then
				# delete them from the list and then repeat until all elements have been 
				# taken care of. This is less memory efficient but works well for when
				# there are a few number of matrix elements per row. 
				row_unique,args = _np.unique(row,return_index=True)
				col_unique = col[args]

				v_out[row_unique] += _np.multiply(v_in[col_unique].T,ME[args]).T
				row = _np.delete(row,args)
				col = _np.delete(col,args)
				ME = _np.delete(ME,args)

		return v_out			

	def Op(self,opstr,indx,J,dtype):
		"""Constructs operator from a site-coupling list and anoperator string in a lattice basis.

		Parameters
		-----------
		opstr : str
			Operator string in the lattice basis format. For instance:
			>>> opstr = "zz"
		indx : list(int)
			List of integers to designate the sites the lattice basis operator is defined on. For instance:
			>>> indx = [2,3]
		J : scalar
			Coupling strength.
		dtype : 'type'
			Data type (e.g. numpy.float64) to construct the operator with.

		Returns
		--------
		tuple 
			`(ME,row,col)`, where
				* numpy.ndarray(scalar): `ME`: matrix elements of type `dtype`.
				* numpy.ndarray(int): `row`: row indices of matrix representing the operator in the lattice basis,
					such that `row[i]` is the row index of `ME[i]`.
				* numpy.ndarray(int): `col`: column index of matrix representing the operator in the lattice basis,
					such that `col[i]` is the column index of `ME[i]`.
			
		Examples
		--------

		>>> J = 1.41
		>>> indx = [2,3]
		>>> opstr = "zz"
		>>> dtype = np.float64
		>>> ME, row, col = Op(opstr,indx,J,dtype)

		"""
		return self._Op(opstr,indx,J,dtype)

	def expanded_form(self,static=[],dynamic=[]):
		"""Splits up operator strings containing "y" and "x" into operator combinations of "+" and "-".

		Parameters
		-----------
		static: list
			Static operators formatted to be passed into the static argument of the `hamiltonian` class.
		dynamic: list
			Dynamic operators formatted to be passed into the dynamic argument of the `hamiltonian` class.

		Returns
		--------
		tuple
			`(static, dynamic)`, where
				* list: `static`: operator strings with "x" and "y" expanded into "+" and "-", formatted to 
					be passed into the static argument of the `hamiltonian` class.
				* list: `dynamic`: operator strings with "x" and "y" expanded into "+" and "-", formatted to 
					be passed into the dynamic argument of the `hamiltonian` class.

		Examples
		---------

		"""
		static_list,dynamic_list = self._get_local_lists(static,dynamic)
		static_list = self._expand_local_list(static_list)
		dynamic_list = self._expand_local_list(dynamic_list)
		static_list,dynamic_list = self._consolidate_local_lists(static_list,dynamic_list)

		static_dict={}
		for opstr,indx,J,ii in static_list:
			indx = list(indx)
			indx.insert(0,J)
			if opstr in static_dict:
				static_dict[opstr].append(indx)
			else:
				static_dict[opstr] = [indx]

		static = [[str(key),list(value)] for key,value in static_dict.items()]

		dynamic_dict={}
		for opstr,indx,J,f,f_args,ii in dynamic_list:
			indx = list(indx)
			indx.insert(0,J)
			if opstr in dynamic_dict:
				dynamic_dict[opstr].append(indx)
			else:
				dynamic_dict[opstr] = [indx]

		dynamic = [[str(key),list(value)] for key,value in dynamic_dict.items()]

		return static,dynamic

	def check_hermitian(self,static,dynamic):
		"""Checks operator string lists for hermiticity of the combined operator.

		Parameters
		-----------
		static: list
			Static operators formatted to be passed into the static argument of the `hamiltonian` class.
		dynamic: list
			Dynamic operators formatted to be passed into the dynamic argument of the `hamiltonian` class.

		Examples
		---------

		"""
		static_list,dynamic_list = self._get_local_lists(static,dynamic)
		static_expand,static_expand_hc,dynamic_expand,dynamic_expand_hc = self._get_hc_local_lists(static_list,dynamic_list)
		# calculate non-hermitian elements
		diff = set( tuple(static_expand) ) - set( tuple(static_expand_hc) )
		
		if diff:
			unique_opstrs = list(set( next(iter(zip(*tuple(diff))))) )
			warnings.warn("The following static operator strings contain non-hermitian couplings: {}".format(unique_opstrs),UserWarning,stacklevel=3)
			try:
				user_input = raw_input("Display all {} non-hermitian couplings? (y or n) ".format(len(diff)) )
			except NameError:
				user_input = input("Display all {} non-hermitian couplings? (y or n) ".format(len(diff)) )

			if user_input == 'y':
				print("   (opstr, indices, coupling)")
				for i in range(len(diff)):
					print("{}. {}".format(i+1, list(diff)[i]))
			raise TypeError("Hamiltonian not hermitian! To turn this check off set check_herm=False in hamiltonian.")
			
			
		# define arbitrarily complicated weird-ass number
		t = _np.cos( (_np.pi/_np.exp(0))**( 1.0/_np.euler_gamma ) )


		# calculate non-hermitian elements
		diff = set( tuple(dynamic_expand) ) - set( tuple(dynamic_expand_hc) )
		if diff:
			unique_opstrs = list(set( next(iter(zip(*tuple(diff))))) )
			warnings.warn("The following dynamic operator strings contain non-hermitian couplings: {}".format(unique_opstrs),UserWarning,stacklevel=3)
			try:
				user_input = raw_input("Display all {} non-hermitian couplings at time t = {}? (y or n) ".format( len(diff), _np.round(t,5)))
			except NameError:
				user_input = input("Display all {} non-hermitian couplings at time t = {}? (y or n) ".format( len(diff), _np.round(t,5)))

			if user_input == 'y':
				print("   (opstr, indices, coupling(t))")
				for i in range(len(diff)):
					print("{}. {}".format(i+1, list(diff)[i]))
			raise TypeError("Hamiltonian not hermitian! To turn this check off set check_herm=False in hamiltonian.")

		print("Hermiticity check passed!")

	def check_symm(self,static,dynamic):
		"""Checks operator string lists for the required symemtries of the combined operator.

		Parameters
		-----------
		static: list
			Static operators formatted to be passed into the static argument of the `hamiltonian` class.
		dynamic: list
			Dynamic operators formatted to be passed into the dynamic argument of the `hamiltonian` class.

		Examples
		---------

		"""
		if self._check_symm is None:
			warnings.warn("Test for symmetries not implemented for {0}, to turn off this warning set check_symm=False in hamiltonian".format(type(self)),UserWarning,stacklevel=3)
			return

		static_blocks,dynamic_blocks = self._check_symm(static,dynamic)

		# define arbitrarily complicated weird-ass number
		t = _np.cos( (_np.pi/_np.exp(0))**( 1.0/_np.euler_gamma ) )

		for symm in static_blocks.keys():
			if len(static_blocks[symm]) == 2:
				odd_ops,missing_ops = static_blocks[symm]
				ops = list(missing_ops)
				ops.extend(odd_ops)
				unique_opstrs = list(set( next(iter(zip(*tuple(ops))))) )
				if unique_opstrs:
					unique_missing_ops = []
					unique_odd_ops = []
					[ unique_missing_ops.append(ele) for ele in missing_ops if ele not in unique_missing_ops]
					[ unique_odd_ops.append(ele) for ele in odd_ops if ele not in unique_odd_ops]
					warnings.warn("The following static operator strings do not obey {0}: {1}".format(symm,unique_opstrs),UserWarning,stacklevel=4)
					try:
						user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops) + len(unique_odd_ops)) )
					except NameError:
						user_input = input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops) + len(unique_odd_ops)) )
					if user_input == 'y':
						print(" these operators are needed for {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_missing_ops):
							print("{0}. {1}".format(i+1, op))
						print(" ")
						print(" these do not obey the {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_odd_ops):
							print("{0}. {1}".format(i+1, op))
					raise TypeError("Hamiltonian does not obey {0}! To turn off check, use check_symm=False in hamiltonian.".format(symm))


			elif len(static_blocks[symm]) == 1:
				missing_ops, = static_blocks[symm]
				unique_opstrs = list(set( next(iter(zip(*tuple(missing_ops))))) )
				if unique_opstrs:
					unique_missing_ops = []
					[ unique_missing_ops.append(ele) for ele in missing_ops if ele not in unique_missing_ops]
					warnings.warn("The following static operator strings do not obey {0}: {1}".format(symm,unique_opstrs),UserWarning,stacklevel=4)
					try:
						user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops)) )
					except NameError:
						user_input = input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops)) )

					if user_input == 'y':
						print(" these operators are needed for {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_missing_ops):
							print("{0}. {1}".format(i+1, op))
					raise TypeError("Hamiltonian does not obey {0}! To turn off check, use check_symm=False in hamiltonian.".format(symm))
			else:
				continue


		for symm in dynamic_blocks.keys():
			if len(dynamic_blocks[symm]) == 2:
				odd_ops,missing_ops = dynamic_blocks[symm]
				ops = list(missing_ops)
				ops.extend(odd_ops)
				unique_opstrs = list(set( next(iter(zip(*tuple(ops))))) )
				if unique_opstrs:
					unique_missing_ops = []
					unique_odd_ops = []
					[ unique_missing_ops.append(ele) for ele in missing_ops if ele not in unique_missing_ops]
					[ unique_odd_ops.append(ele) for ele in odd_ops if ele not in unique_odd_ops]
					warnings.warn("The following dynamic operator strings do not obey {0}: {1}".format(symm,unique_opstrs),UserWarning,stacklevel=4)
					try:
						user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops) + len(unique_odd_ops)) )
					except NameError:
						user_input = input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops) + len(unique_odd_ops)) )

					if user_input == 'y':
						print(" these operators are missing for {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_missing_ops):
							print("{0}. {1}".format(i+1, op))
						print(" ")
						print(" these do not obey {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_odd_ops):
							print("{0}. {1}".format(i+1, op))
					raise TypeError("Hamiltonian does not obey {0}! To turn off check, use check_symm=False in hamiltonian.".format(symm))


			elif len(dynamic_blocks[symm]) == 1:
				missing_ops, = dynamic_blocks[symm]
				unique_opstrs = list(set( next(iter(zip(*tuple(missing_ops))))) )
				if unique_opstrs:
					unique_missing_ops = []
					[ unique_missing_ops.append(ele) for ele in missing_ops if ele not in unique_missing_ops]
					warnings.warn("The following dynamic operator strings do not obey {0}: {1}".format(symm,unique_opstrs),UserWarning,stacklevel=4)
					try:
						user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops)) )
					except NameError:
						user_input = input("Display all {0} couplings? (y or n) ".format(len(unique_missing_ops)) )

					if user_input == 'y':
						print(" these operators are needed for {}:".format(symm))
						print("   (opstr, indices, coupling)")
						for i,op in enumerate(unique_missing_ops):
							print("{0}. {1}".format(i+1, op))
					raise TypeError("Hamiltonian does not obey {0}! To turn off check, use check_symm=False in hamiltonian.".format(symm))
			else:
				continue

		print("Symmetry checks passed!")

	def check_pcon(self,static,dynamic):
		"""Checks operator string lists for particle number (magnetisation) conservartion of the combined operator.

		Parameters
		-----------
		static: list
			Static operators formatted to be passed into the static argument of the `hamiltonian` class.
		dynamic: list
			Dynamic operators formatted to be passed into the dynamic argument of the `hamiltonian` class.

		Examples
		---------

		"""
		if self._check_pcon is None:
			warnings.warn("Test for particle conservation not implemented for {0}, to turn off this warning set check_pcon=False in hamiltonian".format(type(self)),UserWarning,stacklevel=3)
			return

		if self._check_pcon:
			static_list,dynamic_list = self._get_local_lists(static,dynamic)
			static_list_exp = self._expand_local_list(static_list)
			dynamic_list_exp = self._expand_local_list(dynamic_list)
			static_list_exp,dynamic_list_exp = self._consolidate_local_lists(static_list_exp,dynamic_list_exp)
			con = ""

			odd_ops = []
			for opstr,indx,J,ii in static_list_exp:	
				p = opstr.count("+")
				m = opstr.count("-")

				if (p-m) != 0:
					for i in ii:
						if static_list[i] not in odd_ops:
							odd_ops.append(static_list[i])


	
			if odd_ops:
				unique_opstrs = list(set( next(iter(zip(*tuple(odd_ops))))) )
				unique_odd_ops = []
				[ unique_odd_ops.append(ele) for ele in odd_ops if ele not in unique_odd_ops]
				warnings.warn("The following static operator strings do not conserve particle number{1}: {0}".format(unique_opstrs,con),UserWarning,stacklevel=4)
				try:
					user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(odd_ops)) )
				except NameError:
					user_input = input("Display all {0} couplings? (y or n) ".format(len(odd_ops)) )

				if user_input == 'y':
					print(" these operators do not conserve particle number{0}:".format(con))
					print("   (opstr, indices, coupling)")
					for i,op in enumerate(unique_odd_ops):
						print("{0}. {1}".format(i+1, op))
				raise TypeError("Hamiltonian does not conserve particle number{0} To turn off check, use check_pcon=False in hamiltonian.".format(con))

			


			odd_ops = []
			for opstr,indx,J,f,f_args,ii in dynamic_list_exp:	
				p = opstr.count("+")
				m = opstr.count("-")
				if (p-m) != 0:
					for i in ii:
						if dynamic_list[i] not in odd_ops:
							odd_ops.append(dynamic_list[i])

	
			if odd_ops:
				unique_opstrs = list(set( next(iter(zip(*tuple(odd_ops))))))
				unique_odd_ops = []
				[ unique_odd_ops.append(ele) for ele in odd_ops if ele not in unique_odd_ops]
				warnings.warn("The following static operator strings do not conserve particle number{1}: {0}".format(unique_opstrs,con),UserWarning,stacklevel=4)
				try:
					user_input = raw_input("Display all {0} couplings? (y or n) ".format(len(odd_ops)) )
				except NameError:
					user_input = input("Display all {0} couplings? (y or n) ".format(len(odd_ops)) )
				if user_input == 'y':
					print(" these operators do not conserve particle number{0}:".format(con))
					print("   (opstr, indices, coupling)")
					for i,op in enumerate(unique_odd_ops):
						print("{0}. {1}".format(i+1, op))
				raise TypeError("Hamiltonian does not conserve particle number{0} To turn off check, use check_pcon=False in hamiltonian.".format(con))

			print("Particle conservation check passed!")

	def _get__str__(self):
		raise NotImplementedError("basis class: {0} missing implimentation of '_get__str__' required to print out the basis!".format(self.__class__))

	# this methods are optional and are not required for main functions:
	def __iter__(self):
		raise NotImplementedError("basis class: {0} missing implimentation of '__iter__' required for iterating over basis!".format(self.__class__))

	def __getitem__(self,*args,**kwargs):
		raise NotImplementedError("basis class: {0} missing implimentation of '__getitem__' required for '[]' operator!".format(self.__class__))

	# thes methods are required for the symmetry, particle conservation, and hermiticity checks
	def _hc_opstr(self,*args,**kwargs):
		raise NotImplementedError("basis class: {0} missing implimentation of '_hc_opstr' required for hermiticity check! turn this check off by setting test_herm=False".format(self.__class__))

	def _sort_opstr(self,*args,**kwargs):
		raise NotImplementedError("basis class: {0} missing implimentation of '_sort_opstr' required for symmetry and hermiticity checks! turn this check off by setting check_herm=False".format(self.__class__))

	def _expand_opstr(self,*args,**kwargs):
		raise NotImplementedError("basis class: {0} missing implimentation of '_expand_opstr' required for particle conservation check! turn this check off by setting check_pcon=False".format(self.__class__))

	def _non_zero(self,*args,**kwargs):
		raise NotImplementedError("basis class: {0} missing implimentation of '_non_zero' required for particle conservation check! turn this check off by setting check_pcon=False".format(self.__class__))

	def _sort_local_list(self,op_list):
		sorted_op_list = []
		for op in op_list:
			sorted_op_list.append(self._sort_opstr(op))
		sorted_op_list = tuple(sorted_op_list)

		return sorted_op_list

	# this function flattens out the static and dynamics lists to: 
	# [[opstr1,indx11,J11,...],[opstr1,indx12,J12,...],...,[opstrn,indxnm,Jnm,...]]
	# this function gets overridden in photon_basis because the index must be extended to include the photon index.
	def _get_local_lists(self,static,dynamic):
		static_list = []
		for opstr,bonds in static:
			for bond in bonds:
				indx = list(bond[1:])
				J = complex(bond[0])
				static_list.append((opstr,indx,J))

		dynamic_list = []
		for opstr,bonds,f,f_args in dynamic:
			for bond in bonds:
				indx = list(bond[1:])
				J = complex(bond[0])
				dynamic_list.append((opstr,indx,J,f,f_args))

		return self._sort_local_list(static_list),self._sort_local_list(dynamic_list)

	# takes the list from the format given by _get_local_lists and takes the hermitian conjugate of operators.
	def _get_hc_local_lists(self,static_list,dynamic_list):
		static_list_hc = []
		for op in static_list:
			static_list_hc.append(self._hc_opstr(op))

		static_list_hc = tuple(static_list_hc)


		# define arbitrarily complicated weird-ass number
		t = _np.cos( (_np.pi/_np.exp(0))**( 1.0/_np.euler_gamma ) )

		dynamic_list_hc = []
		dynamic_list_eval = []
		for opstr,indx,J,f,f_args in dynamic_list:
			J *= f(t,*f_args)
			op = (opstr,indx,J)
			dynamic_list_hc.append(self._hc_opstr(op))
			dynamic_list_eval.append(self._sort_opstr(op))

		dynamic_list_hc = tuple(dynamic_list_hc)
		
		return static_list,static_list_hc,dynamic_list_eval,dynamic_list_hc

	# this function takes the list format giveb by get_local_lists and expands any operators into the most basic components
	# 'n'(or 'z' for spins),'+','-' If by default one doesn't need to do this then _expand_opstr must do nothing. 
	def _expand_local_list(self,op_list):
		op_list_exp = []
		for i,op in enumerate(op_list):
			new_ops = self._expand_opstr(op,[i])
			for new_op in new_ops:
				if self._non_zero(new_op):
					op_list_exp.append(new_op)

		return self._sort_local_list(op_list_exp)

	def _consolidate_local_lists(self,static_list,dynamic_list):

		static_dict={}
		for opstr,indx,J,ii in static_list:
			if opstr in static_dict:
				if indx in static_dict[opstr]:
					static_dict[opstr][indx][0] += J
					static_dict[opstr][indx][1].extend(ii)
				else:
					static_dict[opstr][indx] = [J,ii]
			else:
				static_dict[opstr] = {indx:[J,ii]}

		static_list = []
		for opstr,opstr_dict in static_dict.items():
			for indx,(J,ii) in opstr_dict.items():
				if J != 0:
					static_list.append((opstr,indx,J,ii))


		dynamic_dict={}
		for opstr,indx,J,f,f_args,ii in dynamic_list:
			if opstr in dynamic_dict:
				if indx in dynamic_dict[opstr]:
					dynamic_dict[opstr][indx][0] += J
					dynamic_dict[opstr][indx][3].extend(ii)
				else:
					dynamic_dict[opstr][indx] = [J,f,f_args,ii]
			else:
				dynamic_dict[opstr] = {indx:[J,f,f_args,ii]}


		dynamic_list = []
		for opstr,opstr_dict in dynamic_dict.items():
			for indx,(J,f,f_args,ii) in opstr_dict.items():
				if J != 0:
					dynamic_list.append((opstr,indx,J,f,f_args,ii))


		return static_list,dynamic_list


def isbasis(obj):
	"""Checks if instance is object of `basis` class.

	Parameters
	-----------
	obj : 
		Arbitraty python object.

	Returns
	--------
	bool
		Can be either of the following:

		* `True`: `obj` is an instance of `basis` class.
		* `False`: `obj` is NOT an instance of `basis` class.

	"""
	return isinstance(obj,basis)


