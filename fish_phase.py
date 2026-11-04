"""Manual visual parrotfish phase labels; never interpreted as confirmed sex."""
PHASES = [('unassessed','Not assessed'),('juvenile','Juvenile (visual)'),('initial','Initial phase (IP)'),('terminal','Terminal phase (TP)'),('transitional','Transitional / intermediate appearance'),('uncertain','Phase uncertain')]
PARROTFISH_GENERA = {'Scarus','Sparisoma','Cryptotomus','Nicholsina','Calotomus','Chlorurus','Cetoscarus','Bolbometopon','Hipposcarus','Leptoscarus'}

def is_parrotfish(species_id,catalog):
    item=catalog.get(species_id,{})
    return item.get('family','').lower()=='scaridae' or item.get('scientific_name','').split(' ')[0] in PARROTFISH_GENERA

def normalize_phase(species_id,catalog,phase=None):
    if not is_parrotfish(species_id,catalog):
        if phase not in (None,'not_applicable','unassessed'):raise ValueError('Visual phase applies only to identified parrotfish')
        return 'not_applicable'
    if phase in (None,'not_applicable'):return 'unassessed'
    if phase not in dict(PHASES):raise ValueError('Unknown visual phase')
    return phase

PHASE_DISPLAY={'unassessed':'Not assessed','juvenile':'Juvenile','initial':'IP','terminal':'TP','transitional':'Transitional','uncertain':'Uncertain','not_applicable':'—'}
