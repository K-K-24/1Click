# xml_parser/extract_fragment.py

# from lxml import etree
# import re

# def extract_relevant_xml(xml_content, search_text, parent_levels=3):
#     """
#     Search for the search_text inside the xml_content,
#     and return a snippet including 'parent_levels' above the found element.
#     """
#     try:
#         # Parse the XML
#         parser = etree.XMLParser(recover=True)
#         root = etree.fromstring(xml_content.encode(), parser=parser)

#         # Find the element containing the search_text
#         matching_element = None

#         for elem in root.iter():
#             if elem.text and search_text.strip() in elem.text.strip():
#                 matching_element = elem
#                 break

#         if matching_element is None:
#             print(f"⚠️ Could not find text '{search_text}' in XML.")
#             return None

#         # Go up to parent_levels
#         context_element = matching_element
#         for _ in range(parent_levels):
#             if context_element.getparent() is not None:
#                 context_element = context_element.getparent()

#         # Get the string of that element
#         snippet = etree.tostring(context_element, pretty_print=True, encoding="unicode")

#         return snippet

#     except Exception as e:
#         print(f"Error during XML fragment extraction: {e}")
#         return None

from lxml import etree
from io import StringIO
import re

def extract_snippet(xml_str, underline_info, n_parents=2):
    """
    Enhanced function to handle complex XML with conkeyrefs where visible text 
    doesn't directly appear in the source XML.
    
    Primary approach: Use comment_id to fetch exact offsets via CCMS API
    Fallback: Use existing strategies based on text, element type, etc.
    
    Args:
        xml_str: The full XML content as string
        underline_info: Dictionary from capture_underlined_text() containing:
          - comment_id (NEW)
          - visible_text
          - href
          - context
          - element_type
          - has_conkeyref
          - parent_path
          - comment_type
        n_parents: Number of parent levels to include in snippet
        
    Returns:
        Tuple of (snippet_xml, xpath_to_target)
    """
    parser = etree.XMLParser(recover=True, remove_blank_text=True)
    root = etree.fromstring(xml_str.encode("utf-8"), parser=parser)

    # Extract all the information from underline_info
    comment_id = underline_info.get("comment_id")  # NEW
    visible_text = underline_info.get("visible_text", "").strip()
    href = underline_info.get("href")
    context = underline_info.get("context", "").strip()
    element_type = underline_info.get("element_type")
    has_conkeyref = underline_info.get("has_conkeyref", False)
    parent_path = underline_info.get("parent_path", "")
    comment_type = underline_info.get("comment_type", "unknown")

    # Check for XML offsets from annotation API
    xml_offsets = underline_info.get("xml_offsets")
    if xml_offsets and 'startOffset' in xml_offsets and 'endOffset' in xml_offsets:
        print(f"🔍 Using annotation offsets: {xml_offsets['startOffset']}-{xml_offsets['endOffset']}")
        try:
            # Convert string XML to list of characters for indexing
            xml_chars = list(xml_str)
            
            # Find the element containing the start offset
            # This is a simplified approach - you might need to adjust for XML structure
            start_offset = int(xml_offsets['startOffset'])
            end_offset = int(xml_offsets['endOffset'])
            
            # Find the nearest valid tag around these offsets
            # Look for an opening tag before the start offset
            tag_start = xml_str.rfind("<", 0, start_offset)
            if tag_start != -1:
                # Find the tag name
                tag_end = xml_str.find(">", tag_start)
                if tag_end != -1 and tag_end > tag_start:
                    tag_content = xml_str[tag_start+1:tag_end]
                    tag_name = tag_content.split()[0]
                    
                    # Try to find the element by tag and position
                    elements = root.xpath(f"//{tag_name}")
                    if elements:
                        # Find the element closest to the offsets
                        for elem in elements:
                            elem_xml = etree.tostring(elem, encoding="unicode")
                            if len(elem_xml) > 0 and start_offset <= xml_str.find(elem_xml) + len(elem_xml) and end_offset >= xml_str.find(elem_xml):
                                target = elem
                                match_method = "annotation_offsets"
                                break
            
            if target:
                print(f"✅ Found element using annotation offsets")
        except Exception as e:
            print(f"⚠️ Error using annotation offsets: {e}")
    
    print(f"🔍 Searching for element matching comment ID: {comment_id}")
    print(f"🔍 Visible text: {visible_text}")
    print(f"ℹ️ Element type: {element_type}, Has conkeyref: {has_conkeyref}")
    
    # Advanced targeting strategy (prioritized)
    target = None
    match_method = None
    
    # NEW: Strategy 0 - Try to find by data-id attribute directly in XML
    if comment_id:
        print(f"🔍 Checking for data-id={comment_id} in XML attributes")
        try:
            # Direct data-id attribute check
            elements = root.xpath(f".//*[@data-id='{comment_id}']")
            if elements:
                target = elements[0]
                match_method = "data_id_attribute"
                print(f"✅ Found element with data-id={comment_id}")
            else:
                # Try other attribute names that might contain the comment_id
                for elem in root.iter():
                    for attr_name, attr_value in elem.attrib.items():
                        if attr_value == comment_id:
                            target = elem
                            match_method = f"found_in_{attr_name}_attribute"
                            print(f"✅ Found comment_id in {attr_name} attribute")
                            break
                    if target:
                        break
        except Exception as e:
            print(f"⚠️ Error searching for data-id in XML: {e}")
    
    # If previous strategy failed and we know the comment_id, try CCMS API
    if not target and comment_id:
        print(f"🔍 Will need to use IXAnnotations API later to locate with comment_id={comment_id}")
        # This would be implemented in the browser automation part
        # We'll rely on existing strategies for now
    
    # Strategy 1: URL/href related changes
    if not target and (href or comment_type == "link" or "url" in context.lower() or "link" in context.lower()):
        print("🔍 Using URL/href targeting strategy")
        
        # Start with xref elements
        xref_elements = root.xpath(".//xref")
        
        if xref_elements:
            print(f"ℹ️ Found {len(xref_elements)} xref elements to examine")
            
            # If we have a specific href, try to match it
            if href:
                for xref in xref_elements:
                    if xref.get("href") == href:
                        target = xref
                        match_method = "href_exact_match"
                        break
            
            # If not found by href, look for xrefs with conkeyref children when has_conkeyref is True
            if not target and has_conkeyref:
                for xref in xref_elements:
                    pnames = xref.xpath(".//pname[@conkeyref]")
                    if pnames:
                        target = xref
                        match_method = "xref_with_conkeyref"
                        break
            
            # Fallback: take first xref if none matched
            if not target and xref_elements:
                target = xref_elements[0]
                match_method = "xref_first"
    
    # Strategy 2: Known element type
    if not target and element_type:
        print(f"🔍 Targeting by element type: {element_type}")
        elements = root.xpath(f".//{element_type}")
        
        if elements:
            # If multiple elements of this type, try text matching
            if visible_text and len(elements) > 1:
                for el in elements:
                    el_text = "".join(el.itertext()).strip()
                    if visible_text in el_text:
                        target = el
                        match_method = f"{element_type}_text_match"
                        break
            
            # If still no target, take the first one
            if not target:
                target = elements[0]
                match_method = f"{element_type}_first"
    
    # Strategy 3: Text matching (for content changes)
    if not target and visible_text:
        print("🔍 Using text content targeting strategy")
        xpath_query = f".//*[contains(normalize-space(), \"{visible_text.replace('\"', '&quot;')}\")]"
        elements = root.xpath(xpath_query)
        
        if elements and len(elements) == 1:
            # If exactly ONE match, we can be confident
            target = elements[0]
            match_method = "single_exact_text_match"
            print(f"✅ Found exactly one element matching the exact text")
        elif elements and len(elements) > 1:
            print(f"⚠️ Found {len(elements)} elements with matching text - need disambiguation")
            # Try to disambiguate using context/neighboring text
            best_match = None
            highest_score = -1
            
            for elem in elements:
                # Get full text including neighbors
                elem_text = ''.join(elem.itertext())
                
                # Compare with context from underline_info
                score = 0
                if context in elem_text:
                    # More context words match = higher score
                    context_words = set(context.lower().split())
                    elem_words = set(elem_text.lower().split())
                    common_words = context_words.intersection(elem_words)
                    score = len(common_words) / len(context_words) if context_words else 0
                
                if score > highest_score:
                    highest_score = score
                    best_match = elem
            
            # Only use best match if score exceeds threshold
            if highest_score > 0.5:  # Adjust threshold as needed
                target = best_match
                match_method = "disambiguated_text_match"
                print(f"✅ Disambiguated between multiple matches with score {highest_score:.2f}")

    
    
    # Strategy 4: Conkeyref attribute (for translated content)
    if not target and has_conkeyref:
        print("🔍 Targeting elements with conkeyref attributes")
        conkeyref_elements = root.xpath(".//*[@conkeyref]")
        
        if conkeyref_elements:
            target = conkeyref_elements[0]
            match_method = "conkeyref_match"
    
    # Final fallback: Try a xpath for list items if parent path suggests a list
    if not target and ("li" in parent_path or "ul" in parent_path):
        print("🔍 Attempting list item targeting based on parent path")
        li_elements = root.xpath(".//li")
        
        if li_elements:
            target = li_elements[0]
            match_method = "list_item_fallback"
    
    if not target:
        raise RuntimeError("❌ Could not find any XML element matching the criteria")
    
    print(f"✅ Found target element using method: {match_method}")
    
    # Get the XML snippet with n_parents
    snippet_root = target
    for _ in range(n_parents):
        parent = snippet_root.getparent()
        if parent is None:
            break
        snippet_root = parent
    
    # Serialize snippet and get xpath
    snippet_xml = etree.tostring(snippet_root, encoding="unicode", pretty_print=True)
    xpath_to_target = root.getroottree().getpath(target)
    
    print(f"📌 Target XPath: {xpath_to_target}")
    return snippet_xml, xpath_to_target

# # Quick test
# if __name__ == "__main__":
#     xml_sample = '''<ul id="ul_djj_r4s_nzb"><li><p><xref format="html" href="https://discovery-center.cloud.sap/serviceCatalog/sap-event-broker" scope="external"><pname conkeyref="loiobe9c73df9e5049119f332a571e8c861e/HANA-CLOUD-EVENT-BROKER-LONG"/></xref></p></li><li><p><xref format="html" href="https://discovery-center.cloud.sap/serviceCatalog/event-mesh" scope="external"><pname conkeyref="loiobe9c73df9e5049119f332a571e8c861e/HANA-CLOUD-ENTERPRISE-MESSAGING-LONG"/></xref></p></li></ul>
#     '''

#     search_text = "subscription management configuration must be updated"
#     snippet = extract_relevant_xml(xml_sample, search_text)

#     print("\nExtracted Snippet:\n", snippet)
