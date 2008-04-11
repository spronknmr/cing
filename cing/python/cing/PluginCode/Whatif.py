"""
    Whatif Module
    First version: gv June 3, 2007
    Second version by jfd.
"""
from cing.Libs.AwkLike import AwkLike
from cing.Libs.NTutils import ExecuteProgram
from cing.Libs.NTutils import NTdebug
from cing.Libs.NTutils import NTdict
from cing.Libs.NTutils import NTerror
from cing.Libs.NTutils import NTlist
from cing.Libs.NTutils import NTmessage
from cing.Libs.NTutils import NTwarning
from cing.Libs.NTutils import sprintf
from cing.core.parameters import cingPaths
from glob import glob
from shutil import copy
from string import upper
import os
import time

# Fix these strings so we can get some automated code checking by pydev extensions.
CHECK_ID_STR     = "checkID"
LOC_ID_STR       = "locID"
LEVEL_STR        = "level"
TEXT_STR         = "text"
TYPE_STR         = "type"
VALUE_LIST_STR   = "valueList"
QUAL_LIST_STR    = "qualList"
WHATIF_STR       = "whatif" # key to the entities (atoms, residues, etc under which the results will be stored

INOCHK_STR       = 'INOCHK'
BNDCHK_STR       = 'BNDCHK'
ANGCHK_STR       = 'ANGCHK'

QUACHK_STR       = 'QUACHK'
RAMCHK_STR       = 'RAMCHK'
C12CHK_STR       = 'C12CHK'
BBCCHK_STR       = 'BBCCHK'
#            QUACHK   Poor   : <   -3.00   Bad    : <   -5.00
#            RAMCHK   Poor   : <   -3.00   Bad    : <   -4.00
#            C12CHK   Poor   : <   -3.00   Bad    : <   -4.00
#            BBCCHK

class Whatif( NTdict ):
    """
    Class to use WHAT IF checks.

    Whatif.checks:                  NTlist instance of individual parsed checks
    Whatif.molSpecificChecks:       NTlist instance of those check pertaining to
                                    molecules; i.e Level : MOLECULE. TODO: implement in What If and here..
    Whatif.residueSpecificChecks:   NTlist instance of those check pertaining to
                                    residues; i.e Level : RESIDUE.
    Whatif.atomSpecificChecks:      NTlist instance of those check pertaining to
                                    atoms; i.e Level : ATOM.
    Whatif.residues:                NTdict instance with results of all
                                    residueSpecificChecks, sorted by key residue.
    Whatif.atoms:                   NTdict instance with results of all
                                    atomSpecificChecks sorted by key atom.

    Individual checks:
    NTdict instances with keys pointing to NTlist instances;

    All file references relative to rootPath ('.' by default) using the .path()
    method.
    TODO:   - Use hydrogen atoms
            - For more details see: http://spreadsheets.google.com/pub?key=p1emRxxfe3f4PkJ798dwPIg
                and sf.net
    """
    #define some more user friendly names
    # List of defs at:
    # http://www.yasara.org/pdbfinder_file.py.txt
    # http://swift.cmbi.ru.nl/whatif/html/chap23.html
    # All are in text record of file to be parsed so they're kind of redundant.
    nameDefs =[
                ('ACCLST', 'Relative accessibility'),
                ('ALTATM', 'Amino acids inside ligands check/Attached group check'),
                ('ANGCHK', 'Angles'),
                ('BA2CHK', 'Hydrogen bond acceptors'),
                ('BBCCHK', 'Backbone normality'),
                ('BH2CHK', 'Hydrogen bond donors'),
                ('BMPCHK', 'Bumps'),
                ('BNDCHK', 'Bond lengths'),
                ('BVALST', 'B-Factors'),
                ('C12CHK', 'Chi-1 chi-2'),
                ('CHICHK', 'Torsions'),
                ('CCOCHK', 'Inter-chain connection check'),
                ('CHICHK', 'Torsion angle check'),
                ('DUNCHK', 'Duplicate atom names in ligands'),
                ('EXTO2',  'Test for extra OXTs'),
                ('FLPCHK', 'Peptide flip'),
                ('HNDCHK', 'Chirality'),
                ('HNQCHK', 'Flip HIS GLN ASN hydrogen-bonds'),
                ('INOCHK', 'Accessibility'),
                ('MISCHK', 'Missing atoms'),
                ('MO2CHK', 'Missing C-terminal oxygen atoms'),
                ('NAMCHK', 'Atom names'),
                ('NQACHK', 'Qualities'),
                ('PC2CHK', 'Proline puckers'),
                ('PDBLST', 'List of residues'),
                ('PL2CHK', 'Connections to aromatic rings'),
                ('PL3CHK', 'Side chain planarity with hydrogens attached'),
                ('PLNCHK', 'Protein side chain planarities'),
                ('PRECHK', 'Missing backbone atoms.'),
                ('PUCCHK', 'Ring puckering in Prolines'),
                ('QUACHK', 'Directional Atomic Contact Analysis'),
                ('RAMCHK', 'Ramachandran'),
                ('ROTCHK', 'Rotamers'),
                ('SCOLST', 'List of symmetry contacts'),
                ('TO2CHK', 'Missing C-terminal groups'),
                ('TOPPOS', 'Ligand without know topology'),
                ('WGTCHK', 'Atomic occupancy check'),
                ('Hand',   '(Pro-)chirality or handness check')
               ]
    debugCheck = 'BNDCHK'
    # Create a dictionary for fast lookup.
    nameDict = NTdict()
    for n1,n2 in nameDefs:
        nameDict[n1] = n2
    nameDict.keysformat()
    recordKeyWordsToIgnore = { # Using a dictionary for fast key checks below.
                              "Bad":None,
                              "Date":None,
                              "DocURL":None,
                              "ID":None,
                              "LText":None,
                              "Poor":None,
                              "Program":None,
                              "Text":None,
                              "Version":None
                              }
#    recordKeyWordsToIgnore.append( "IGNORE" ) # Added by JFD


    scriptBegin = """
# Generate WI script
# Set WI options
# Truncating errors in a PDBOUT table
SETWIF 593 100
# Should Q atoms be considered hydrogen atoms?
SETWIF 1505 1
# Read all models
#SETWIF 847 1
# Not adding C-terminal O if missing
SETWIF 1071 1
# We have an NMR structure (curiously set to No here)
SETWIF 1503 0
# IUPAC atom nomenclature
SETWIF 142 1
# Cutoff for reporting in the INP* routines (*100)
SETWIF 143 400
# General debug flag
# Should prevent problems such as:
# > 1b9q and many others: broken backbone/ERROR reading DSSP file
# > 1ehj Zero length in torsion calculation
SETWIF 1012 0
"""
    scriptPerModel = """
# Read the one model
%fulchk
$pdb_file
xxx

$mv check.db check_$modelNumberString.db

# Initialize the soup
%inisou

# Keep the line above empty.
"""

    scriptQuit = """
fullstop y
"""
# Run whatif with the script



    def __init__( self, rootPath = '.', molecule = None, **kwds ):
        NTdict.__init__( self, __CLASS__ = WHATIF_STR, **kwds )
        self.checks                = None
        self.molSpecificChecks     = None
        self.residueSpecificChecks = None
        self.atomSpecificChecks    = None
        self.residues              = None
        self.atoms                 = None
        self.molecule              = molecule
        self.rootPath              = rootPath
    #end def

    def path( self, *args ):
        """Return path relative to rootPath """
        return os.path.join( self.rootPath, *args )
    #end def

#    def _dictDictList( self, theDict, name, key ):
#        """
#            Internal routine that returns a NTlist instance for theDict[name][key].
#            Also put in translated key.
#        """
#        d = theDict.setdefault( name, NTdict() )
#        d[self.nameDict[key]] = d.setdefault( key, NTlist() )

    def _parseCheckdb( self, modelCheckDbFileName, model ):
        """Parse check_001.db etc. Generate references to
           all checks. Storing the check data according to residue and atom.
           Return self on success or 
           True on error.

        Example of parsed data structure:
        E.g. check can have attributes like: 
        [                                          # checks
            {                                      # curCheck
            "checkID":  "BNDCHK"
            "level":    "RESIDUE"
            "type":     "FLOAT"
            "locId": {                             # curLocDic
                "'A- 189-GLU'"                     # curLocId
                    : {                            # curListDic
                    "valeList": [ 0.009, 0.100 ]
                    "qualList": ["POOR", "GOOD" ]
                    },
                "'A- 188-ILE'": {
                    "valeList": [ 0.01, 0.200 ]
                    "qualList": ["POOR", "GOOD" ]
                    }}},]
           """
           
        # Parser uses sense of current items as per below.
        curModelId = model - 1
        curCheck   = None # Can be used to skip ahead.
        curLocId   = None
        curLocDic  = None
        curListDic = None 
        isTypeFloat= False
        
        if not self.checks: # This will be called multiple times so don't overwrite.
            self.checks = NTlist()
        for line in AwkLike( modelCheckDbFileName, minNF = 3 ):
#            NTdebug("DEBUG: read: "+line.dollar[0])
            if line.dollar[2] != ':':
                NTwarning("The line below was unexpectedly not parsed, expected second field to be a semicolon.")
                NTwarning(line.dollar[0])

#            Split a line of the check.db file
            a      = line.dollar[0].split(':')
            key    = a[0].strip()
            value  = a[1].strip()
            
            if self.recordKeyWordsToIgnore.has_key(key):
                continue

            if key == 'CheckID':
                curCheck = None
                checkID = value # local var within this 'if' statement. 
#                NTdebug("found check ID: " + checkID)
                if not self.nameDict.has_key( checkID ):
                    NTerror("Skipping an unknown CheckID: "+checkID)
                    continue
#                if self.debugCheck != checkID:
##                    NTdebug("Skipping a check not to be debugged: "+checkID)
#                    continue
                isTypeFloat = False
                
                if self.has_key( checkID ):
                    curCheck = self.get(checkID)
                else:
                    curCheck = NTdict()
                    self.checks.append( curCheck )
                    curCheck[CHECK_ID_STR] = checkID
                    self[ checkID ] = curCheck
#                    NTdebug("Appended check: "+checkID)
                # Set the curLocDic in case of the first time otherwise get.
                curLocDic = curCheck.setdefault(LOC_ID_STR, NTdict())
                continue
            if not curCheck: # First pick up a check.
                continue
            
#            NTdebug("found key, value: [" + key + "] , [" + value + "]")
            if key == "Text":
                curCheck[TEXT_STR] = value
                continue
            if key == "Level":
                curCheck[LEVEL_STR] = upper(value) # check Hand has level "Residue" which should be upped.
                continue
            if key == "Type":
                curCheck[TYPE_STR] = value
                if value == "FLOAT":
                    isTypeFloat = True
                continue            
            if key == "Name":
                curLocId = value
#                NTdebug("curLocId: "+curLocId )
                curListDic = curLocDic.setdefault(curLocId, NTdict())
                continue

#           Only allow values so lines like:
#            #    Value :  1.000
#            #    Qual  : BAD
            if key == "Value":
                keyWord = VALUE_LIST_STR
            elif  key == "Qual":
                keyWord = QUAL_LIST_STR
            else:
                NTerror( "Expected key to be Value or Qual but found key, value pair: [%s] [%s]" % ( key, value ))
                return None
            
            if not curListDic.has_key( keyWord ):
                itemNTlist = NTlist()
                curListDic[ keyWord ] = itemNTlist
                for _dummy in range(self.molecule.modelCount): # Shorter code for these 2 lines please JFD.
                    itemNTlist.append(None)
#                NTdebug("b initialized with Nones: itemNTlist: %r", itemNTlist )
            else:
                itemNTlist = curListDic[ keyWord ]
#            NTdebug("a itemNTlist: "+`itemNTlist` )

            if isTypeFloat:
                itemNTlist[curModelId] = float(value)
            else:
                itemNTlist[curModelId] = value
#            NTdebug("c itemNTlist: "+`itemNTlist` )
#            NTdebug("For key       : "+key)
#            NTdebug("For modelID   : "+`model`)
#            NTdebug("For value     : "+value)
#            NTdebug("For check     : "+`curCheck`)
#            NTdebug("For keyed list: "+`curCheck[key]`)
#            NTdebug("For stored key: "+`curCheck[key][modelId]`)
        #end for each line.

    def _processCheckdb( self   ):
        """ 
        Put parsed data of all models into CING data model
        Return None for success
        
        Example of processed data structure attached to say a residue:
            "whatif": {
                "ANGCHK": {
                    "valeList": [ 0.009, 0.100 ],
                    "qualList": ["POOR", "GOOD" ]},
                "BNDCHK": {
                    "valeList": [ 0.009, 0.100 ],
                    }}"""
                    
        NTmessage("Now processing the check results into CING data model")
        # Assemble the atom, residue and molecule specific checks
        # set the formats of each check easy printing
#        self.molecule.setAllChildrenByKey( WHATIF_STR, None)
        self.molecule.whatif = self # is self and that's asking for luggage 
        # Later                   
        
        
#        self.molSpecificChecks     = NTlist()
        self.residueSpecificChecks = NTlist()
        self.atomSpecificChecks    = NTlist()

#        self.mols     = NTdict(MyName="Mol")
        self.residues = NTdict(MyName="Res")
        self.atoms    = NTdict(MyName="Atom")
#        levelIdList     = ["MOLECULE", "RESIDUE", "ATOM" ]
        levelIdList     = [ "RESIDUE", "ATOM" ]
        selfLevels      = [ self.residues, self.atoms ]
        selfLevelChecks = [ self.residueSpecificChecks, self.atomSpecificChecks ]
        # sorting on mols, residues, and atoms
#        NTmessage("  for self.checks: " + `self.checks`)
        NTdebug("  for self.checks count: " + `len(self.checks)`)
        for check in self.checks:
            if LEVEL_STR not in check:
                NTerror("no level attribute in check dictionary: "+check[CHECK_ID_STR])
                NTerror("check dictionary: "+`check`)
                return True
#            NTdebug("attaching check: "+check[CHECK_ID_STR]+" of type: "+check[TYPE_STR] + " to level: "+check[LEVEL_STR])
            idx = levelIdList.index( check[LEVEL_STR] )
            if idx < 0:
                NTerror("Unknown Level ["+check[LEVEL_STR]+"] in check:"+check[CHECK_ID_STR]+' '+check[TEXT_STR])
                return True
            selfLevelChecks[idx].append( check )
            check.keysformat()

        checkIter = iter(selfLevelChecks)
        for _levelEntity in selfLevels:
            levelCheck = checkIter.next()
#            NTdebug("working on levelEntity: " + levelEntity.MyName +"levelCheck: " + `levelCheck`[:80])
            for check in levelCheck:
                checkId = check[CHECK_ID_STR]
#                NTdebug( 'check        : ' + `check`)
#                NTdebug( 'check[CHECK_ID_STR]: ' + checkId)
                if not check.has_key(LOC_ID_STR):
                    NTdebug("There is no %s attribute, skipping check: [%s]" % ( LOC_ID_STR, check ))
                    NTdebug("  check: "+ `check`)
                    continue
                curLocDic = check[LOC_ID_STR]
                if not curLocDic:
#                    NTdebug("Skipping empty locationsDic")
                    continue
                
                for curLocId in curLocDic.keys():
                    curListDic = curLocDic[curLocId]                
#                    NTdebug("Working on curLocId:   " + `curLocId`)
#                    NTdebug("Working on curListDic: " + `curListDic`)
                    
                    nameTuple = self.translateResAtmString( curLocId )
                    if not nameTuple:
                        NTerror('Whatif._processCheckdb: parsing entity "%s" what if descriptor' % curLocId)
                        continue
                    entity = self.molecule.decodeNameTuple( nameTuple ) # can be a chain, residue or atom level object
                    if not entity:
                        NTerror('Whatif._processCheckdb: mapping entity "%s" descriptor' % curLocId)
                        continue
#                    NTdebug("adding to entity: " + `entity`)
                    entityWhatifDic = entity.setdefault(WHATIF_STR, NTdict())
#                    NTdebug("adding to entityWhatifDic: " + `entityWhatifDic`)
                                        
                    keyWordList = [ VALUE_LIST_STR, QUAL_LIST_STR]
#            "locId": {                             # curLocDic
#                "'A- 189-GLU'"                     # curLocId
#                    : {                            # curListDic
#                    "valeList": [ 0.009, 0.100 ]   # curList
#                    "qualList": ["POOR", "GOOD" ]
                    
                    for keyWord in keyWordList:
                        curList = curListDic.getDeepByKeys(keyWord) # just 1 level deep but never set as setdefaults would do.
                        if not curList:
                            continue                        
                        entityWhatifCheckDic = entityWhatifDic.setdefault(checkId, NTdict())
                        entityWhatifCheckDic[keyWord]=curList
#                    NTdebug("now entityWhatifDic: " + `entityWhatifDic`)
        NTmessage('done with _processCheckdb')
    #end def

    def translateResAtmString( self, string ):
        """Internal routine to split the residue or atom identifier string
            of the check.db file. E.g.:
            A- 187-HIS- CB 
            A- 177-GLU
            return None for error            
            """
        try:
            a = string.split('-')
            t = ['PDB',a[0].strip(),int(a[1]), None]
            if len(a) == 4: # Is there an atom name too?
                t[3] = a[3].strip() 
            return tuple( t )
        except:
            return None

    def report( self ):
        return ''.join( file( self.path( Whatif.reportFile ), 'r').readlines())
#end Class

def runWhatif( project, tmp=None ):
    """
        Run and import the whatif results per model.
        All models in the ensemble of the molecule will be checked.
        Set whatif references for Molecule, Chain, Residue and Atom instances
        or None if no whatif results exist
        returns 1 on success
    """
    if not project.molecule:
        NTerror("No project molecule in runWhatCheck")
        return True

    path = project.path( project.molecule.name, project.moleculeDirectories.whatif )
    if not os.path.exists( path ):
        project.molecule.whatif = None
        for chain in project.molecule.allChains():
            chain.whatif = None
        for res in project.molecule.allResidues():
            res.whatif = None
        for atm in project.molecule.allAtoms():
            atm.whatif = None
        return True

    whatif = Whatif( rootPath = path, molecule = project.molecule )
    if project.molecule == None:
        NTerror('in runWhatif: no molecule defined\n')
        return True

    if project.molecule.modelCount == 0:
        NTerror('in runWhatif: no models for "%s"\n', project.molecule)
        return True

    for res in project.molecule.allResidues():
        if not (res.hasProperties('protein') or res.hasProperties('nucleic')):
            NTwarning('non-standard residue %s found and will be written out for What If\n' % `res`)

    models = NTlist(*range( 1,project.molecule.modelCount+1 ))

    whatifDir = project.mkdir( project.molecule.name, project.moleculeDirectories.whatif  )
    whatifPath       = os.path.dirname(cingPaths.whatif)
    whatifTopology   = os.path.join(whatifPath, "dbdata","TOPOLOGY.H")
    whatifExecutable = os.path.join(whatifPath, "DO_WHATIF.COM")

    copy(whatifTopology, os.path.join(whatifDir,"TOPOLOGY.FIL"))

    for model in models:
        fullname =  os.path.join( whatifDir, sprintf('model_%03d.pdb', model) )
        # WI prefers IUPAC like PDB now. In CING the closest is BMRBd?
        NTmessage('==> Materializing model '+`model`+" to disk" )
        pdbFile = project.molecule.toPDB( model=model, convention = "BMRB" )
        if not pdbFile:
            NTerror("Failed to write a temporary file with a model's coordinate")
            return True
        pdbFile.save( fullname   )

    scriptComplete = Whatif.scriptBegin
    for model in models:
        modelNumberString = sprintf('%03d', model)
        modelFileName = 'model_'+modelNumberString+".pdb"
        scriptModel = Whatif.scriptPerModel.replace("$pdb_file", modelFileName)
        scriptModel = scriptModel.replace("$modelNumberString", modelNumberString)
        scriptComplete += scriptModel
    scriptComplete += Whatif.scriptQuit
    # Let's ask the user to be nice and not kill us
    # estimate to do (400/7) residues per minutes as with entry 1bus on dual core intel Mac.
    totalNumberOfResidues = project.molecule.modelCount * len(project.molecule.allResidues())
    timeRunEstimatedInSeconds    = totalNumberOfResidues / 13.
    timeRunEstimatedInSecondsStr = sprintf("%.0f",timeRunEstimatedInSeconds)
    NTmessage('==> Running What If checks on '+`totalNumberOfResidues`+
                 " residues for an estimated (13 residues/s): "+timeRunEstimatedInSecondsStr+" seconds; please wait")
    if totalNumberOfResidues < 100:
        NTmessage("It takes much longer per residue for a small molecule/ensemble")
    scriptFileName = "whatif.script"
    scriptFullFileName =  os.path.join( whatifDir, scriptFileName )
    open(scriptFullFileName,"w").write(scriptComplete)
    whatifProgram = ExecuteProgram( whatifExecutable, rootPath = whatifDir,
                             redirectOutput = True, redirectInputFromDummy = True )
    # The last argument becomes a necessary redirection into fouling What If into
    # thinking it's running interactively.
    now = time.time()
    if True:
        whatifExitCode = whatifProgram("script", scriptFileName )
    else:
        NTdebug("Skipping actual whatif execution for testing")
        whatifExitCode = 0

    NTdebug("Took number of seconds: " + sprintf("%8.1f", time.time() - now))
    if whatifExitCode:
        NTerror("Failed whatif checks with exit code: " + `whatifExitCode`)
        return True

    try:
        removeListLocal = ["DSSPOUT", "TOPOLOGY.FIL", "PDBFILE.PDB", "pdbout.tex"]
        removeList = []
        for fn in removeListLocal:
            removeList.append( os.path.join(whatifDir, fn) )

        for extension in [ "*.eps", "*.pdb", "*.LOG", "*.DAT", "*.SCC", "*.sty", "*.FIG"]:
            for fn in glob(os.path.join(whatifDir,extension)):
                removeList.append(fn)
        for fn in removeList:
            if not os.path.exists(fn):
                NTdebug("Expected to find a file to be removed but it doesn't exist: " + fn )
                continue
#            NTdebug("Removing: " + fn)
            os.unlink(fn)
    except:
        NTwarning("Failed to remove all temporary what if files that were expected")

    for model in models:
        modelNumberString = sprintf('%03d', model)
#        fullname =  os.path.join( whatifDir, sprintf('model_%03d.pdb', model) )
#        os.unlink( fullname ) 
        modelCheckDbFileName = "check_"+modelNumberString+".db"
        NTmessage('==> Parsing checks for model '+modelCheckDbFileName)
        modelCheckDbFullFileName =  os.path.join( whatifDir, modelCheckDbFileName )
        if whatif._parseCheckdb( modelCheckDbFullFileName, model ):
            NTerror("Failed to parse check db")
            return True
            
    if whatif._processCheckdb():
        NTerror("Failed to process check db")
        return True
#end def

def criticizeByWhatif( project ):
    NTmessage('What If passes opportunity to critique. A first.')

# register the function
methods  = [
            (runWhatif, None),
            (criticizeByWhatif, None),
                        ]