#!/usr/bin/env python3
# Portions copyright 2012 Google Inc. All Rights Reserved.
# This file has been modified by NICTA

# This file is part of pyphe.
#
# pyphe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyphe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyphe.  If not, see <http://www.gnu.org/licenses/>.

"""Paillier encryption library for partially homomorphic encryption."""
import random

try:
    from collections.abc import Mapping
except ImportError:
    Mapping = dict

from phe import EncodedNumber
from phe.util import invert, powmod, getprimeover, isqrt

# Paillier cryptosystem is based on integer factorisation.
# The default is chosen to give a minimum of 128 bits of security.
# https://www.keylength.com/en/4/
DEFAULT_KEYSIZE = 2048


def generate_paillier_keypair(private_keyring=None, n_length=DEFAULT_KEYSIZE):
    """Return a new :class:`PaillierPublicKey` and :class:`PaillierPrivateKey`.

    Add the private key to *private_keyring* if given.

    Args:
      private_keyring (PaillierPrivateKeyring): a
        :class:`PaillierPrivateKeyring` on which to store the private
        key.
      n_length: key size in bits.

    Returns:
      tuple: The generated :class:`PaillierPublicKey` and
      :class:`PaillierPrivateKey`
    """
    p = q = n = None
    n_len = 0
    while n_len != n_length:
        p = getprimeover(n_length // 2)
        q = p
        while q == p:
            q = getprimeover(n_length // 2)
        n = p * q
        nsquare = n * n
        n_len = n.bit_length()

    random_alpha = random.randrange(34359738368) % nsquare
    public_key = PaillierPublicKey(n,p,q, random_alpha)
    private_key = PaillierPrivateKey(public_key, p, q, random_alpha)

    if private_keyring is not None:
        private_keyring.add(private_key)

    return public_key, private_key

def genKeyShares(privatekey,publickey):
    nsquare = publickey.nsquare
    rand1 = random.randrange(privatekey.sk // 2) % nsquare
    while True:
        rand2 = (privatekey.sk - rand1) %nsquare
        if(privatekey.sk == rand1 + rand2):
            break
    s1 = PaillierPrivateKey(publickey,publickey.p,publickey.q,rand1)
    s2 = PaillierPrivateKey(publickey,publickey.p,publickey.q,rand2)
    return s1,s2

def raw_transform(keyshare,publickey,encrypted_number):
    ciphertext = encrypted_number.ciphertext
    if not isinstance(ciphertext, dict):
        raise TypeError('Expected ciphertext to be a dict, not: %s' %
                type(ciphertext))
    A = ciphertext['A']
    A1 = invert(ciphertext['A'],publickey.nsquare)
    t2 = powmod(A1,keyshare.sk,publickey.nsquare)
    t3 = ciphertext['B']
    t4=t3*t2
    B=t4%publickey.nsquare
    transformed_cipher = {"A":A,"B":B}
    print('transformerssssss',transformed_cipher)
    encrypted_number.ciphertext = transformed_cipher
    return encrypted_number

def transform_encoded(keyshare,publickey,encrypted_number):
    if not isinstance(encrypted_number, EncryptedNumber):
        raise TypeError('Expected encrypted_number to be an EncryptedNumber not: %s' % type(encrypted_number))
    if keyshare.public_key != encrypted_number.public_key:
        raise ValueError('encrypted_number was encrypted against a '
                             'different key!')
    #Encoding = EncodedNumber
    print('original cipher',encrypted_number.ciphertext)
    encoded = raw_transform(keyshare,publickey,encrypted_number)
    return encoded

def transform(keyshare,publickey,encrypted_number):
    transformed_ciphertext = transform_encoded(keyshare, publickey,encrypted_number)
    print(transformed_ciphertext)
    return transformed_ciphertext

def finalDecrypt(keyshare,publickey,encrypted_number):
    m=keyshare.decrypt(encrypted_number)
    return m


class PaillierPublicKey(object):
    """Contains a public key and associated encryption methods.

    Args:

      n (int): the modulus of the public key - see Paillier's paper.

    Attributes:
      g (int): part of the public key - see Paillier's paper.
      n (int): part of the public key - see Paillier's paper.
      k (int): part of public parameters
      nsquare (int): :attr:`n` ** 2, stored for frequent use.
      max_int (int): Maximum int that may safely be stored. This can be
        increased, if you are happy to redefine "safely" and lower the
        chance of detecting an integer overflow.
    """
    def __init__(self, n,p,q, random_alpha):
        self.n = n
        #self.g = n + 1
        self.nsquare = n * n
        self.random_alpha = random_alpha % self.nsquare
        self.p = p
        self.q = q
        self.pp = self.p - 1 // 2
        self.qq = self.q -1 // 2
        self.g = random.randrange(1048576)
        self.max_int = n // 3 - 1
        one = powmod (1,1,self.nsquare)
        ppqq=self.pp*self.qq
        k = powmod(self.g,ppqq,self.n)
        self.k = k - 1 // self.n
        self.MK ={"pp":self.pp,"qq":self.qq}
        self.h = powmod(self.g, self.random_alpha,self.nsquare)
        #self.max_int = n // 3 - 1


    def __repr__(self):
        publicKeyHash = hex(hash(self))[2:]
        return "<PaillierPublicKey {}>".format(publicKeyHash[:10])

    def __eq__(self, other):
        return self.n == other.n

    def __hash__(self):
        return hash(self.n)

    def raw_encrypt(self, plaintext, r_value=None):
        """Paillier encryption of a positive integer plaintext < :attr:`n`.

        You probably should be using :meth:`encrypt` instead, because it
        handles positive and negative ints and floats.

        Args:
          plaintext (int): a positive integer < :attr:`n` to be Paillier
            encrypted. Typically this is an encoding of the actual
            number you want to encrypt.
          r_value (int): obfuscator for the ciphertext; by default (i.e.
            r_value is None), a random value is used.

        Returns:
          int: Paillier encryption of plaintext.

        Raises:
          TypeError: if plaintext is not an int.
        """
        if not isinstance(plaintext, int):
            raise TypeError('Expected int type plaintext but got: %s' %
                            type(plaintext))

        #if self.n - self.max_int <= plaintext < self.n:
            # Very large plaintext, take a sneaky shortcut using inverses
            #neg_plaintext = self.n - plaintext  # = abs(plaintext - nsquare)
            #neg_ciphertext = (self.n * neg_plaintext + 1) % self.nsquare
            #nude_ciphertext = invert(neg_ciphertext, self.nsquare)
        #else:
            # we chose g = n + 1, so that we can exploit the fact that
            # (n+1)^plaintext = n*plaintext + 1 mod n^2
        
        nude_ciphertext = (self.n * plaintext + 1) % self.nsquare

        r = random.randrange(256) % self.nsquare
        obfuscator_hr = powmod(self.h, r, self.nsquare)

        obfuscator_gr = powmod(self.g, r, self.nsquare)
        A = obfuscator_gr

        B = (nude_ciphertext * obfuscator_hr) % self.nsquare
        ciphertext = {"A":A,"B":B}
        return ciphertext

    def get_random_lt_n(self):
        """Return a cryptographically random number less than :attr:`n`"""
        return random.SystemRandom().randrange(1, self.n)

    def encrypt(self, value, precision=None, r_value=None):
        """Encode and Paillier encrypt a real number *value*.

        Args:
          value: an int or float to be encrypted.
            If int, it must satisfy abs(*value*) < :attr:`n`/3.
            If float, it must satisfy abs(*value* / *precision*) <<
            :attr:`n`/3
            (i.e. if a float is near the limit then detectable
            overflow may still occur)
          precision (float): Passed to :meth:`EncodedNumber.encode`.
            If *value* is a float then *precision* is the maximum
            **absolute** error allowed when encoding *value*. Defaults
            to encoding *value* exactly.
          r_value (int): obfuscator for the ciphertext; by default (i.e.
            if *r_value* is None), a random value is used.

        Returns:
          EncryptedNumber: An encryption of *value*.

        Raises:
          ValueError: if *value* is out of range or *precision* is so
            high that *value* is rounded to zero.
        """

        if isinstance(value, EncodedNumber):
            encoding = value
        else:
            encoding = EncodedNumber.encode(self, value, precision)

        return self.encrypt_encoded(encoding, r_value)

    def encrypt_encoded(self, encoding, r_value):
        """Paillier encrypt an encoded value.

        Args:
          encoding: The EncodedNumber instance.
          r_value (int): obfuscator for the ciphertext; by default (i.e.
            if *r_value* is None), a random value is used.

        Returns:
          EncryptedNumber: An encryption of *value*.
        """
        # If r_value is None, obfuscate in a call to .obfuscate() (below)
        #obfuscator = r_value or 1
        ciphertext = self.raw_encrypt(encoding.encoding)
        encrypted_number = EncryptedNumber(self, ciphertext, encoding.exponent)
        return encrypted_number


class PaillierPrivateKey(object):
    """Contains a private key and associated decryption method.

    Args:
      public_key (:class:`PaillierPublicKey`): The corresponding public
        key.
      p (int): private secret - see Paillier's paper.
      q (int): private secret - see Paillier's paper.

    Attributes:
      public_key (PaillierPublicKey): The corresponding public
        key.
      p (int): private secret - see Paillier's paper.
      q (int): private secret - see Paillier's paper.
      psquare (int): p^2
      qsquare (int): q^2
      p_inverse (int): p^-1 mod q
      hp (int): h(p) - see Paillier's paper.
      hq (int): h(q) - see Paillier's paper.
    """
    def __init__(self, public_key, p, q, random_alpha):
        self.public_key = public_key
        self.p = p
        self.q = q
        self.psquare = self.p * self.p

        self.qsquare = self.q * self.q
        self.n = self.p * self.q
        self.nsquare = self.n * self.n
        self.random_alpha = random_alpha
        #self.p_inverse = invert(self.p, self.q)
        self.pp = (self.p - 1) // 2
        self.qq = (self.q - 1) // 2
        #self.hp = self.h_function(self.p, self.psquare)
        #self.hq = self.h_function(self.q, self.qsquare)
        self.sk = self.random_alpha % self.nsquare

    @staticmethod
    def from_totient(public_key, totient):
        """given the totient, one can factorize the modulus

        The totient is defined as totient = (p - 1) * (q - 1),
        and the modulus is defined as modulus = p * q

        Args:
          public_key (PaillierPublicKey): The corresponding public
            key
          totient (int): the totient of the modulus

        Returns:
          the :class:`PaillierPrivateKey` that corresponds to the inputs

        Raises:
          ValueError: if the given totient is not the totient of the modulus
            of the given public key
        """
        p_plus_q = public_key.n - totient + 1
        p_minus_q = isqrt(p_plus_q * p_plus_q - public_key.n * 4)
        q = (p_plus_q - p_minus_q) // 2
        p = p_plus_q - q
        if not p*q == public_key.n:
            raise ValueError('given public key and totient do not match.')
        return PaillierPrivateKey(public_key, p, q, random_alpha)

    def __repr__(self):
        pub_repr = repr(self.public_key)
        return "<PaillierPrivateKey for {}>".format(pub_repr)

    def genKeyShares(self):
        nsquare = self.public_key.nsquare
        publickey = self.public_key
        rand1 = random.randrange(self.sk // 2) % nsquare
        while True:
            rand2 = (self.sk - rand1) %nsquare
            if(self.sk == rand1 + rand2):
                break
        s1 = PaillierPrivateKey(publickey,publickey.p,publickey.q,rand1)
        s2 = PaillierPrivateKey(publickey,publickey.p,publickey.q,rand2)
        return s1,s2

    def raw_transform(self,encrypted_number):
        ciphertext = encrypted_number.ciphertext
        if not isinstance(ciphertext, dict):
            raise TypeError('Expected ciphertext to be a dict, not: %s' % type(ciphertext))
        A = ciphertext['A']
        A1 = invert(ciphertext['A'],self.public_key.nsquare)
        t2 = powmod(A1,self.sk,self.public_key.nsquare)
        t3 = ciphertext['B']
        t4=t3*t2
        B=t4%self.public_key.nsquare
        transformed_cipher = {"A":A,"B":B}
        print('transformerssssss',transformed_cipher)
        encrypted_number.ciphertext = transformed_cipher
        return encrypted_number

    def transform_encoded(self,encrypted_number):
        if not isinstance(encrypted_number, EncryptedNumber):
            raise TypeError('Expected encrypted_number to be an EncryptedNumber not: %s' % type(encrypted_number))
        if self.public_key != encrypted_number.public_key:
            raise ValueError('encrypted_number was encrypted against a '
                             'different key!')
        #Encoding = EncodedNumber
        print('original cipher',encrypted_number.ciphertext)
        encoded = self.raw_transform(encrypted_number)
        return encoded

    def transform(self,encrypted_number):
        transformed_ciphertext = self.transform_encoded(encrypted_number)
        print(transformed_ciphertext)
        return transformed_ciphertext

    def finalDecrypt(self,encrypted_number):
        m=self.decrypt(encrypted_number)
        return m

    def decrypt(self, encrypted_number):
        """Return the decrypted & decoded plaintext of *encrypted_number*.

        Uses the default :class:`EncodedNumber`, if using an alternative encoding
        scheme, use :meth:`decrypt_encoded` or :meth:`raw_decrypt` instead.

        Args:
          encrypted_number (EncryptedNumber): an
            :class:`EncryptedNumber` with a public key that matches this
            private key.

        Returns:
          the int or float that `EncryptedNumber` was holding. N.B. if
            the number returned is an integer, it will not be of type
            float.

        Raises:
          TypeError: If *encrypted_number* is not an
            :class:`EncryptedNumber`.
          ValueError: If *encrypted_number* was encrypted against a
            different key.
        """
        encoded = self.decrypt_encoded(encrypted_number)
        return encoded.decode()
        

    def decrypt_encoded(self, encrypted_number, Encoding=None):
        """Return the :class:`EncodedNumber` decrypted from *encrypted_number*.

        Args:
          encrypted_number (EncryptedNumber): an
            :class:`EncryptedNumber` with a public key that matches this
            private key.
          Encoding (class): A class to use instead of :class:`EncodedNumber`, the
            encoding used for the *encrypted_number* - used to support alternative
            encodings.

        Returns:
          :class:`EncodedNumber`: The decrypted plaintext.

        Raises:
          TypeError: If *encrypted_number* is not an
            :class:`EncryptedNumber`.
          ValueError: If *encrypted_number* was encrypted against a
            different key.
        """
        if not isinstance(encrypted_number, EncryptedNumber):
            raise TypeError('Expected encrypted_number to be an EncryptedNumber'
                            ' not: %s' % type(encrypted_number))

        if self.public_key != encrypted_number.public_key:
            raise ValueError('encrypted_number was encrypted against a '
                             'different key!')

        if Encoding is None:
            Encoding = EncodedNumber

        encoded = self.raw_decrypt(encrypted_number.ciphertext)
        print('encoded_decrpyed',encoded)
        return Encoding(self.public_key, encoded,
                             encrypted_number.exponent)

    def raw_decrypt(self, ciphertext):
        """Decrypt raw ciphertext and return raw plaintext.

        Args:
          ciphertext (int): (usually from :meth:`EncryptedNumber.ciphertext()`)
            that is to be Paillier decrypted.

        Returns:
          int: Paillier decryption of ciphertext. This is a positive
          integer < :attr:`public_key.n`.

        Raises:
          TypeError: if ciphertext is not an int.
        """
        if not isinstance(ciphertext, dict):
            raise TypeError('Expected ciphertext to be a dict, not: %s' %
                type(ciphertext))

        #decrypt_to_p = self.l_function(powmod(ciphertext, self.p-1, self.psquare), self.p) * self.hp % self.p
        #decrypt_to_q = self.l_function(powmod(ciphertext, self.q-1, self.qsquare), self.q) * self.hq % self.q
        #return self.crt(decrypt_to_p, decrypt_to_q)

        t1=invert(ciphertext['A'],self.nsquare)
        t2=powmod(t1,self.sk,self.nsquare)
        t3=ciphertext['B']
        t4=t3*t2
        one=powmod(1,1,self.nsquare)
        t5=t4 - one
        t6=t5%self.nsquare
        m = t6 // self.n
        return m

    def h_function(self, x, xsquare):
        """Computes the h-function as defined in Paillier's paper page 12,
        'Decryption using Chinese-remaindering'.
        """
        return invert(self.l_function(powmod(self.public_key.g, x - 1, xsquare),x), x)

    def l_function(self, x, p):
        """Computes the L function as defined in Paillier's paper. That is: L(x,p) = (x-1)/p"""
        return (x - 1) // p

    def crt(self, mp, mq):
        """The Chinese Remainder Theorem as needed for decryption. Returns the solution modulo n=pq.

        Args:
           mp(int): the solution modulo p.
           mq(int): the solution modulo q.
       """
        u = (mq - mp) * self.p_inverse % self.q
        return mp + (u * self.p)

    def __eq__(self, other):
        return self.p == other.p and self.q == other.q

    def __hash__(self):
        return hash((self.p, self.q))


class PaillierPrivateKeyring(Mapping):
    """Holds several private keys and can decrypt using any of them.

    Acts like a dict, supports :func:`del`, and indexing with **[]**,
    but adding keys is done using :meth:`add`.

    Args:
      private_keys (list of PaillierPrivateKey): an optional starting
        list of :class:`PaillierPrivateKey` instances.
    """
    def __init__(self, private_keys=None):
        if private_keys is None:
            private_keys = []
        public_keys = [k.public_key for k in private_keys]
        self.__keyring = dict(zip(public_keys, private_keys))

    def __getitem__(self, key):
        return self.__keyring[key]

    def __len__(self):
        return len(self.__keyring)

    def __iter__(self):
        return iter(self.__keyring)

    def __delitem__(self, public_key):
        del self.__keyring[public_key]

    def add(self, private_key):
        """Add a key to the keyring.

        Args:
          private_key (PaillierPrivateKey): a key to add to this keyring.
        """
        if not isinstance(private_key, PaillierPrivateKey):
            raise TypeError("private_key should be of type PaillierPrivateKey, "
                            "not %s" % type(private_key))
        self.__keyring[private_key.public_key] = private_key

    def decrypt(self, encrypted_number):
        """Return the decrypted & decoded plaintext of *encrypted_number*.

        Args:
          encrypted_number (EncryptedNumber): encrypted against a known public
            key, i.e., one for which the private key is on this keyring.

        Returns:
          the int or float that *encrypted_number* was holding. N.B. if
          the number returned is an integer, it will not be of type
          float.

        Raises:
          KeyError: If the keyring does not hold the private key that
            decrypts *encrypted_number*.
        """
        relevant_private_key = self.__keyring[encrypted_number.public_key]
        return relevant_private_key.decrypt(encrypted_number)


class EncryptedNumber(object):
    """Represents the Paillier encryption of a float or int.

    Typically, an `EncryptedNumber` is created by
    :meth:`PaillierPublicKey.encrypt`. You would only instantiate an
    `EncryptedNumber` manually if you are de-serializing a number
    someone else encrypted.


    Paillier encryption is only defined for non-negative integers less
    than :attr:`PaillierPublicKey.n`. :class:`EncodedNumber` provides
    an encoding scheme for floating point and signed integers that is
    compatible with the partially homomorphic properties of the Paillier
    cryptosystem:

    1. D(E(a) * E(b)) = a + b
    2. D(E(a)**b)     = a * b

    where `a` and `b` are ints or floats, `E` represents encoding then
    encryption, and `D` represents decryption then decoding.

    Args:
      public_key (PaillierPublicKey): the :class:`PaillierPublicKey`
        against which the number was encrypted.
      ciphertext (int): encrypted representation of the encoded number.
      exponent (int): used by :class:`EncodedNumber` to keep track of
        fixed precision. Usually negative.

    Attributes:
      public_key (PaillierPublicKey): the :class:`PaillierPublicKey`
        against which the number was encrypted.
      exponent (int): used by :class:`EncodedNumber` to keep track of
        fixed precision. Usually negative.

    Raises:
      TypeError: if *ciphertext* is not an int, or if *public_key* is
        not a :class:`PaillierPublicKey`.
    """
    def __init__(self, public_key, ciphertext, exponent=0):
        self.public_key = public_key
        self.ciphertext = ciphertext
        self.exponent = exponent
        self.__is_obfuscated = False
        if isinstance(self.ciphertext, EncryptedNumber):
            raise TypeError('ciphertext should be a dictionary')
        if not isinstance(self.public_key, PaillierPublicKey):
            raise TypeError('public_key should be a PaillierPublicKey')

    def __add__(self, other):
        """Add an int, float, `EncryptedNumber` or `EncodedNumber`."""
        if isinstance(other, EncryptedNumber):
            return self._add_encrypted(other)
        elif isinstance(other, EncodedNumber):
            return self._add_encoded(other)
        else:
            return self._add_scalar(other)

    def __radd__(self, other):
        """Called when Python evaluates `34 + <EncryptedNumber>`
        Required for builtin `sum` to work.
        """
        return self.__add__(other)

    def __mul__(self, other):
        """Multiply by an int, float, or EncodedNumber."""
        if isinstance(other, EncryptedNumber):
            raise NotImplementedError('Good luck with that...')

        if isinstance(other, EncodedNumber):
            encoding = other
        else:
            encoding = EncodedNumber.encode(self.public_key, other)
            print('encodingencodingencoding', type(encoding.encoding))
        product = self._raw_mul(encoding.encoding)
        exponent = self.exponent + encoding.exponent

        return EncryptedNumber(self.public_key, product, exponent)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __sub__(self, other):
        return self + (other * -1)

    def __rsub__(self, other):
        return other + (self * -1)

    def __truediv__(self, scalar):
        return self.__mul__(1 / scalar)

    def ciphertext(self):
        """Return the ciphertext of the EncryptedNumber.

        Choosing a random number is slow. Therefore, methods like
        :meth:`__add__` and :meth:`__mul__` take a shortcut and do not
        follow Paillier encryption fully - every encrypted sum or
        product should be multiplied by r **
        :attr:`~PaillierPublicKey.n` for random r < n (i.e., the result
        is obfuscated). Not obfuscating provides a big speed up in,
        e.g., an encrypted dot product: each of the product terms need
        not be obfuscated, since only the final sum is shared with
        others - only this final sum needs to be obfuscated.

        Not obfuscating is OK for internal use, where you are happy for
        your own computer to know the scalars you've been adding and
        multiplying to the original ciphertext. But this is *not* OK if
        you're going to be sharing the new ciphertext with anyone else.

        So, by default, this method returns an obfuscated ciphertext -
        obfuscating it if necessary. If instead you set `be_secure=False`
        then the ciphertext will be returned, regardless of whether it
        has already been obfuscated. We thought that this approach,
        while a little awkward, yields a safe default while preserving
        the option for high performance.

        Args:
          be_secure (bool): If any untrusted parties will see the
            returned ciphertext, then this should be True.

        Returns:
          an int, the ciphertext. If `be_secure=False` then it might be
            possible for attackers to deduce numbers involved in
            calculating this ciphertext.
        """
        """if be_secure and not self.__is_obfuscated:
            #self.obfuscate()
        """
        return self.ciphertext

    def decrease_exponent_to(self, new_exp):
        """Return an EncryptedNumber with same value but lower exponent.

        If we multiply the encoded value by :attr:`EncodedNumber.BASE` and
        decrement :attr:`exponent`, then the decoded value does not change.
        Thus we can almost arbitrarily ratchet down the exponent of an
        `EncryptedNumber` - we only run into trouble when the encoded
        integer overflows. There may not be a warning if this happens.

        When adding `EncryptedNumber` instances, their exponents must
        match.

        This method is also useful for hiding information about the
        precision of numbers - e.g. a protocol can fix the exponent of
        all transmitted `EncryptedNumber` instances to some lower bound(s).

        Args:
          new_exp (int): the desired exponent.

        Returns:
          EncryptedNumber: Instance with the same plaintext and desired
            exponent.

        Raises:
          ValueError: You tried to increase the exponent.
        """
        if new_exp > self.exponent:
            raise ValueError('New exponent %i should be more negative than '
                             'old exponent %i' % (new_exp, self.exponent))
        multiplied = self * pow(EncodedNumber.BASE, self.exponent - new_exp)
        multiplied.exponent = new_exp
        return multiplied

    def obfuscate(self):
        """Disguise ciphertext by multiplying by r ** n with random r.

        This operation must be performed for every `EncryptedNumber`
        that is sent to an untrusted party, otherwise eavesdroppers
        might deduce relationships between this and an antecedent
        `EncryptedNumber`.

        For example::

            enc = public_key.encrypt(1337)
            send_to_nsa(enc)       # NSA can't decrypt (we hope!)
            product = enc * 3.14
            send_to_nsa(product)   # NSA can deduce 3.14 by bruteforce attack
            product2 = enc * 2.718
            product2.obfuscate()
            send_to_nsa(product)   # NSA can't deduce 2.718 by bruteforce attack
        """
        r = self.public_key.get_random_lt_n()
        r_pow_n = powmod(r, self.public_key.n, self.public_key.nsquare)
        self.__ciphertext['A'] = self.__ciphertext['A'] * r_pow_n % self.public_key.nsquare
        self.__is_obfuscated = True

    def _add_scalar(self, scalar):
        """Returns E(a + b), given self=E(a) and b.

        Args:
          scalar: an int or float b, to be added to `self`.

        Returns:
          EncryptedNumber: E(a + b), calculated by encrypting b and
            taking the product of E(a) and E(b) modulo
            :attr:`~PaillierPublicKey.n` ** 2.

        Raises:
          ValueError: if scalar is out of range or precision.
        """
        encoded = EncodedNumber.encode(self.public_key, scalar,
                                       max_exponent=self.exponent)

        return self._add_encoded(encoded)

    def _add_encoded(self, encoded):
        """Returns E(a + b), given self=E(a) and b.

        Args:
          encoded (EncodedNumber): an :class:`EncodedNumber` to be added
            to `self`.

        Returns:
          EncryptedNumber: E(a + b), calculated by encrypting b and
            taking the product of E(a) and E(b) modulo
            :attr:`~PaillierPublicKey.n` ** 2.

        Raises:
          ValueError: if scalar is out of range or precision.
        """
        if self.public_key != encoded.public_key:
            raise ValueError("Attempted to add numbers encoded against "
                             "different public keys!")

        # In order to add two numbers, their exponents must match.
        a, b = self, encoded
        if a.exponent > b.exponent:
            a = self.decrease_exponent_to(b.exponent)
        elif a.exponent < b.exponent:
            b = b.decrease_exponent_to(a.exponent)

        # Don't bother to salt/obfuscate in a basic operation, do it
        # just before leaving the computer.
        encrypted_scalar = a.public_key.encrypt(b.encoding)

        sum_ciphertext = a._raw_add(encrypted_scalar)
        return EncryptedNumber(a.public_key, sum_ciphertext, a.exponent)

    def _add_encrypted(self, other):
        """Returns E(a + b) given E(a) and E(b).

        Args:
          other (EncryptedNumber): an `EncryptedNumber` to add to self.

        Returns:
          EncryptedNumber: E(a + b), calculated by taking the product
            of E(a) and E(b) modulo :attr:`~PaillierPublicKey.n` ** 2.

        Raises:
          ValueError: if numbers were encrypted against different keys.
        """
        if self.public_key != other.public_key:
            raise ValueError("Attempted to add numbers encrypted against "
                             "different public keys!")

        # In order to add two numbers, their exponents must match.
        a, b = self, other
        if a.exponent > b.exponent:
            a = self.decrease_exponent_to(b.exponent)
        elif a.exponent < b.exponent:
            b = b.decrease_exponent_to(a.exponent)

        sum_ciphertext = a._raw_add(b)
        return EncryptedNumber(a.public_key, sum_ciphertext, a.exponent)

    def _raw_add(self,other):
        """Returns the integer E(a + b) given ints E(a) and E(b).

        N.B. this returns an int, not an `EncryptedNumber`, and ignores
        :attr:`ciphertext`

        Args:
          e_a (int): E(a), first term
          e_b (int): E(b), second term

        Returns:
          int: E(a + b), calculated by taking the product of E(a) and
            E(b) modulo :attr:`~PaillierPublicKey.n` ** 2.
        """
     
        ciphertext1 = self.ciphertext
        ciphertext2 = other.ciphertext
        text={}
        text['A'] = (ciphertext1['A'] * ciphertext2['A'])%self.public_key.nsquare
        text['B'] = (ciphertext1['B'] * ciphertext2['B'])%self.public_key.nsquare
        return text 

    def _raw_mul(self, plaintext):
        """Returns the integer E(a * plaintext), where E(a) = ciphertext

        Args:
          plaintext (int): number by which to multiply the
            `EncryptedNumber`. *plaintext* is typically an encoding.
            0 <= *plaintext* < :attr:`~PaillierPublicKey.n`

        Returns:
          int: Encryption of the product of `self` and the scalar
            encoded in *plaintext*.

        Raises:
          TypeError: if *plaintext* is not an int.
          ValueError: if *plaintext* is not between 0 and
            :attr:`PaillierPublicKey.n`.
        """
        a,b = self, plaintext
        if not isinstance(plaintext, int):
            raise TypeError('Expected ciphertext to be int, not %s' %
                type(plaintext))

        if plaintext < 0 or plaintext >= self.public_key.n:
            raise ValueError('Scalar out of bounds: %i' % plaintext)

        if self.public_key.n - self.public_key.max_int <= plaintext:
            # Very large plaintext, play a sneaky trick using inverses
            neg_c = invert(self.ciphertext, self.public_key.nsquare)
            neg_scalar = self.public_key.n - plaintext
            return powmod(neg_c, neg_scalar, self.public_key.nsquare)
        else:
            return a.exponentiate(plaintext)

    def exponentiate(self,m):
        ciphertext=self.ciphertext
        text ={}   
        text['A'] = powmod(ciphertext['A'],m, self.public_key.nsquare)
        text['B'] = powmod(ciphertext['B'],m,self.public_key.nsquare)
        return text  


"""
pub_key, pri_key = generate_paillier_keypair()
cipher = pub_key.encrypt(1001)
cipher2 = pub_key.encrypt(10.1)
cipher3 = cipher + cipher2
#m=pri_key.decrypt(cipher3)
#print(m)
s1,s2=genKeyShares(pri_key,pub_key)
s3,s4=s2.genKeyShares()
print('s2.sk',s2.sk)
print('s1.sk',s1.sk)
print('pri_key.sk',pri_key.sk)
cipher4=s1.transform(cipher3)
cipher5=s3.transform(cipher4)
m2=s4.finalDecrypt(cipher5)

print(m2)
"""
