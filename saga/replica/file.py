

from   saga.engine.logger import getLogger
from   saga.engine.engine import getEngine, ANY_ADAPTOR
from   saga.task          import SYNC, ASYNC, TASK
from   saga.url           import Url
from   saga.replica       import *

import saga.exceptions
import saga.attributes


# permissions.Permissions, task.Async
class LogicalFile (object) :


    def __init__ (self, url=None, flags=READ, session=None, _adaptor=None) : 
        '''
        url:       saga.Url
        flags:     flags enum
        session:   saga.Session
        ret:       obj
        '''

        file_url = Url (url)

        self._is_recursive = False # recursion guard (NOTE: NOT THREAD SAFE)

        self._session = session
        self._engine  = getEngine ()
        self._logger  = getLogger ('saga.replica.LogicalFile')
        self._logger.debug ("saga.replica.LogicalFile.__init__ (%s, %s)"  \
                         % (str(file_url), str(session)))

        if _adaptor :
            # created from adaptor
            self._adaptor = _adaptor
            self._adaptor.init_instance (url, flags, session)
        else :
            self._adaptor = self._engine.get_adaptor (self, 'saga.replica.LogicalFile', file_url.scheme, \
                                                      None, ANY_ADAPTOR, file_url, flags, session)


    @classmethod
    def create (self, url=None, flags=READ, ttype=None) :
        '''
        url:       saga.Url
        flags:     saga.replica.flags enum
        session:   saga.Session
        ttype:     saga.task.type enum
        ret:       saga.Task
        '''

        file_url = Url (url)
    
        engine = getEngine ()
        logger = getLogger ('saga.replica.LogicalFile.create')
        logger.debug ("saga.replica.LogicalFile.create(%s, %s, %s)"  \
                   % (str(file_url), str(session), str(ttype)))
    
        # attempt to find a suitable adaptor, which will call 
        # init_instance_async(), which returns a task as expected.
        return engine.get_adaptor (self, 'saga.replica.LogicalFile', file_url.scheme, \
                                   ttype, ANY_ADAPTOR, file_url, session)


    @classmethod
    def _create_from_adaptor (self, url, flags, session, adaptor_name) :
        '''
        url:          saga.Url
        flags:        saga.replica.flags enum
        session:      saga.Session
        adaptor_name: String
        ret:          saga.replica.LogicalFile (bound to a specific adaptor)
        '''

        engine = getEngine ()
        logger = getLogger ('saga.replica.LogicalFile')
        logger.debug ("saga.replica.LogicalFile._create_from_adaptor (%s, %s, %s)"  \
                   % (url, flags, adaptor_name))
    
    
        # attempt to find a suitable adaptor, which will call 
        # init_instance_sync(), resulting in 
        # FIXME: self is not an instance here, but the class object...
        adaptor = engine.get_adaptor (self, 'saga.replica.LogicalFile', url.scheme, None, adaptor_name)
    
        return self (url, flags, session, _adaptor=adaptor)


    # ----------------------------------------------------------------
    #
    # namespace entry methods
    #
    def get_url (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           saga.Url / saga.Task
        '''
        return self._adaptor.get_url (ttype=ttype)

  
    def get_cwd (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           string / saga.Task
        '''
        return self._adaptor.get_cwd (ttype=ttype)
  
    
    def get_name (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           string / saga.Task
        '''
        return self._adaptor.get_name (ttype=ttype)
  
    
    def is_dir_self (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           bool / saga.Task
        '''
        return self._adaptor.is_dir_self (ttype=ttype)
  
    
    def is_entry_self (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           bool / saga.Task
        '''
        return self._adaptor.is_entry_self (ttype=ttype)
  
    
    def is_link_self (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           bool / saga.Task
        '''
        return self._adaptor.is_link_self (ttype=ttype)
  
    
    def read_link_self (self, ttype=None) :
        '''
        ttype:         saga.task.type enum
        ret:           saga.Url / saga.Task
        '''
        return self._adaptor.read_link_self (ttype=ttype)
  
    
    def copy_self (self, tgt, flags=None, ttype=None) :
        '''
        tgt:           saga.Url
        flags:         enum flags
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''

        # ------------------------------------------------------------
        # parameter checks
        tgt_url = Url (tgt)  # ensure valid and typed Url


        # async ops don't deserve a fallback (yet)
        if ttype != None :
            return self._adaptor.copy_self (tgt_url, flags, ttype=ttype)


        try :
            # we have only sync calls here - attempt a normal call to the bound
            # adaptor first (doh!)
            ret = self._adaptor.copy_self (tgt_url, flags, ttype=ttype)
        
        except saga.exceptions.SagaException as e :
            # if we don't have a scheme for tgt, all is in vain (adaptor
            # should have handled a relative path...)
            if not tgt_url.scheme :
                raise e

            # So, the adaptor bound to the src URL did not manage to copy the file.
            # If the tgt has a scheme set, we try again with other matching file 
            # adaptors,  by setting (a copy of) the *src* URL to the same scheme,
            # in the hope that other adaptors can copy from localhost.
            #
            # In principle that mechanism can also be used for remote copies, but
            # URL translation is way more fragile in those cases...
            
            # check recursion guard
            if self._is_recursive :
                self._logger.debug("fallback recursion detected - abort")
              
            else :
                # activate recursion guard
                self._is_recursive += 1

                # find applicable adaptors we could fall back to, i.e. which
                # support the tgt schema
                adaptor_names = self._engine.find_adaptors
                ('saga.replica.LogicalFile', tgt_url.scheme)

                self._logger.debug("try fallback copy to these adaptors: %s" % adaptor_names)

                # build a new src url, by switching to the target schema
                tmp_url        = self.get_url ()
                tmp_url.scheme = tgt_url.scheme

                for adaptor_name in adaptor_names :
                  
                    try :
                        self._logger.info("try fallback copy to %s" % adaptor_name)

                        # get an tgt-scheme'd adaptor for the new src url, and try copy again
                        adaptor = self._engine.get_adaptor (self, 'saga.replica.LogicalFile', \
                                                            tgt_url.scheme, None, adaptor_name)
                        tmp     = saga.replica.LogicalFile (tmp_url, READ, self._session, _adaptor=adaptor)

                        ret = tmp.copy_self (tgt_url, flags)

                        # release recursion guard
                        self._is_recursive -= 1

                        # if nothing raised an exception so far, we are done.
                        return 


                    except saga.exceptions.SagaException as e :

                        self._logger.info("fallback failed: %s" % e)

                        # didn't work, ignore this adaptor
                        pass

            # if all was in vain, we rethrow the original exception
            self._is_recursive -= 1
            raise e
  
    
    def link_self (self, tgt, flags=None, ttype=None) :
        '''
        tgt:           saga.Url
        flags:         enum flags
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.link_self (tgt, flags, ttype=ttype)
  
    
    def move_self (self, tgt, flags=None, ttype=None) :
        '''
        tgt:           saga.Url
        flags:         flags enum
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.move_self (tgt, flags, ttype=ttype)
  
    
    def remove_self (self, flags=None, ttype=None) :
        '''
        flags:         flags enum
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.remove_self (flags, ttype=ttype)
  
    
    def close (self, timeout=None, ttype=None) :
        '''
        timeout:       float
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.close (timeout, ttype=ttype)
  
    
    def permissions_allow_self (self, id, perms, flags=None, ttype=None) :
        '''
        id:            string
        perms:         saga.permissions.flags enum
        flags:         flags enum
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.permissions_allow_self (id, perms, flags, ttype=ttype)
  
    
    def permissions_deny_self (self, id, perms, flags=None, ttype=None) :
        '''
        id:            string
        perms:         saga.permissions.flags enum
        flags:         flags enum
        ttype:         saga.task.type enum
        ret:           None / saga.Task
        '''
        return self._adaptor.permissions_deny_self (id, perms, flags, ttype=ttype)
  
  
    url  = property (get_url)   # saga.Url
    cwd  = property (get_cwd)   # string
    name = property (get_name)  # string



    # ----------------------------------------------------------------
    #
    # replica methods
    #
    def is_file_self (self, ttype=None) :
        '''
        ttype:    saga.task.type enum
        ret:      bool / saga.Task
        '''
        return self._adaptor.is_file_self (ttype=ttype)

  
    def get_size_self (self, ttype=None) :
        '''
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.get_size_self (ttype=ttype)

  
    def read (self, size=-1, ttype=None) :
        '''
        size :    int
        ttype:    saga.task.type enum
        ret:      string / bytearray / saga.Task
        '''
        return self._adaptor.read (size, ttype=ttype)

  
    def write (self, data, ttype=None) :
        '''
        data :    string / bytearray
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.write (data, ttype=ttype)

  
    def seek (self, off, whence=START, ttype=None) :
        '''
        off :     int
        whence:   seek_mode enum
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.seek (off, whence, ttype=ttype)

  
    def read_v (self, iovecs, ttype=None) :
        '''
        iovecs:   list [tuple (int, int)]
        ttype:    saga.task.type enum
        ret:      list [bytearray] / saga.Task
        '''
        return self._adaptor.read_v (iovecs, ttype=ttype)

  
    def write_v (self, data, ttype=None) :
        '''
        data:     list [tuple (int, string / bytearray)]
        ttype:    saga.task.type enum
        ret:      list [int] / saga.Task
        '''
        return self._adaptor.write_v (data, ttype=ttype)

  
    def size_p (self, pattern, ttype=None) :
        '''
        pattern:  string 
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.size_p (pattern, ttype=ttype)
  

    def read_p (self, pattern, ttype=None) :
        '''
        pattern:  string
        ttype:    saga.task.type enum
        ret:      string / bytearray / saga.Task
        '''
        return self._adaptor.read_p (pattern, ttype=ttype)

  
    def write_p (self, pattern, data, ttype=None) :
        '''
        pattern:  string
        data:     string / bytearray
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.write_p (pattern, data, ttype=ttype)

  
    def modes_e (self, ttype=None) :
        '''
        ttype:    saga.task.type enum
        ret:      list [string] / saga.Task
        '''
        return self._adaptor.modes_e (ttype=ttype)

  
    def size_e (self, emode, spec, ttype=None) :
        '''
        emode:    string
        spec:     string
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.size_e (emode, spec, ttype=ttype)

  
    def read_e (self, emode, spec, ttype=None) :
        '''
        emode:    string
        spec:     string
        ttype:    saga.task.type enum
        ret:      bytearray / saga.Task
        '''
        return self._adaptor.read_e (emode, spec, ttype=ttype)

  
    def write_e (self, emode, spec, data, ttype=None) :
        '''
        emode:    string
        spec:     string
        data:     string / bytearray
        ttype:    saga.task.type enum
        ret:      int / saga.Task
        '''
        return self._adaptor.read_e (emode, spec, data, ttype=ttype)

  
    size  = property (get_size_self)  # int
    modes = property (modes_e)  # int
  
  