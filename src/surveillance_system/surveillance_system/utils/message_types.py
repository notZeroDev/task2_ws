def parse_detected_objects(msg_data):
    """
    Parses the standard string message from the object_detector_node.
    Returns a list of dictionaries with parsed detection info.
    """
    detections = []
    if not msg_data:
        return detections
        
    items = msg_data.split('; ')
    for item in items:
        # Expected format: "label 0.95 [x1,y1,x2,y2]"
        try:
            parts = item.split(' ')
            if len(parts) >= 3:
                label = parts[0]
                conf = float(parts[1])
                coords_str = item[item.find("[")+1:item.find("]")]
                x1, y1, x2, y2 = map(int, coords_str.split(','))
                
                detections.append({
                    'label': label,
                    'confidence': conf,
                    'bbox': [x1, y1, x2, y2]
                })
        except Exception:
            continue
            
    return detections
